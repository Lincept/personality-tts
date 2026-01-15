"""
主测试脚本 - LLM + TTS 集成测试
支持实时流式对话和实时语音播放
采用两阶段结构化输出记忆管理方案
支持多种运行模式：
- 文字对话模式：你打字，AI 说话
- 语音对话模式：你说话，AI 说话（支持 AEC 回声消除）
"""
import os
import sys
import json
import logging
import time
import argparse
import threading
from typing import Optional

from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm.llm_client import LLMClient
from src.tts.qwen3_realtime_tts import Qwen3RealtimeTTS
from src.tts.volcengine_realtime_tts import VolcengineRealtimeTTS
from src.audio.pyaudio_player import PyAudioStreamPlayer
from src.config_loader import ConfigLoader
from src.realtime_pipeline import RealtimeStreamingPipeline
from src.voice_assistant_prompt import VoiceAssistantPrompt
from src.role_loader import RoleLoader
from src.memory.mem0_manager import Mem0Manager
from src.memory.memory_chat import MemoryEnhancedChat
from src.asr import DashScopeASR, AudioInput, InterruptController
from src.asr.aec_processor import SimpleAEC

def _parse_log_level(value: str) -> Optional[int]:
    """Parse log level from env; return None for 'OFF' (disable logging)."""
    if value is None:
        return logging.INFO
    v = str(value).strip().upper()
    if v in {"OFF", "NONE", "DISABLE", "FALSE", "0"}:
        return None
    if v.isdigit():
        return int(v)
    return getattr(logging, v, logging.INFO)


# 尽早加载 .env，保证 import 阶段就能按环境变量控制日志
load_dotenv()

_level = _parse_log_level(os.getenv("PTTS_LOG_LEVEL"))
if _level is None:
    logging.disable(logging.CRITICAL)
else:
    # force=True 确保即使其它模块已配置过 handler 也能按环境变量重新配置
    logging.basicConfig(level=_level, force=True)
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        h.setLevel(_level)

    # 常见噪声来源：HTTP 客户端、WebSocket、以及本项目的 memory_chat
    for name in ("httpx", "httpcore", "websocket", "websockets", "memory_chat"):
        logging.getLogger(name).setLevel(_level)


class VoiceInteractiveMode:
    """语音交互模式 - 支持语音输入和打断，集成 AEC 回声消除"""

    def __init__(self, enable_aec: bool = True, device_index: Optional[int] = None, asr_model: str = "paraformer-realtime-v2", role_config: dict = None):
        """
        初始化语音交互模式

        Args:
            enable_aec: 是否启用 AEC（回声消除）- 需要配置聚合设备
            device_index: 音频设备索引（聚合设备的索引，启用 AEC 时必须提供）
            asr_model: ASR 模型选择
                - "paraformer-realtime-v2": Paraformer 实时模型 v2（推荐，准确度高）
                - "fun-asr-realtime-2025-11-07": FunASR 2025 版本（默认）
            role_config: 角色配置
        """
        # 加载环境变量
        env_vars = load_env_file()
        api_key = (
            env_vars.get('QWEN3_API_KEY') or os.getenv('QWEN3_API_KEY') or
            env_vars.get('DASHSCOPE_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
        )

        if not api_key:
            raise ValueError(
                '未找到 DashScope API Key，请在 .env 中设置 QWEN3_API_KEY 或 DASHSCOPE_API_KEY'
            )

        # 仅展示脱敏信息，方便排查是否读取到了 Key
        print(f"🔑 DashScope Key: {_mask_secret(api_key)}")

        # 加载角色配置
        role_loader = RoleLoader()
        if role_config is None:
            role_config = role_loader.get_role("xuejie")

        # 初始化主程序
        self.llm_tts = LLMTTSTest(role_config=role_config)

        # 提前校验 LLM 配置，避免进入语音流程后才 401
        llm_cfg = self.llm_tts.config.get("openai_compatible", {})
        if not llm_cfg.get("api_key"):
            raise ValueError(
                '未找到 LLM 的 OPENAI_API_KEY，请在 .env 中配置 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL'
            )
        self.llm_tts.initialize_llm()

        # 初始化 ASR
        self.asr = DashScopeASR(api_key=api_key, model=asr_model)
        print(f"🎤 ASR 模型: {asr_model}")

        # 初始化 AEC 处理器（如果启用）
        self.enable_aec = enable_aec
        self.aec_processor = None

        if enable_aec:
            # 检查是否提供了设备索引
            if device_index is None:
                raise ValueError(
                    '启用 AEC 时必须提供聚合设备索引！\n'
                    '请先运行: python -m src.main --list-devices\n'
                    '然后使用: python -m src.main --voice --device-index <索引>'
                )

            try:
                self.aec_processor = SimpleAEC(sample_rate=16000)
                print("🎛️ AEC（回声消除）已启用 - 使用聚合设备 + BlackHole")
            except Exception as e:
                print(f"⚠️ AEC 初始化失败: {e}")
                print("   将继续运行但不使用 AEC")
                self.enable_aec = False

        # 初始化音频输入（传入 AEC 处理器和聚合设备配置）
        # 使用 WebRTC 标准帧大小：10ms = 160 samples @ 16kHz
        self.audio_input = AudioInput(
            sample_rate=16000,
            chunk_size=160,  # 修改为 10ms（WebRTC 标准）
            enable_aec=self.enable_aec,
            aec_processor=self.aec_processor,
            use_aggregate_device=enable_aec,  # 启用 AEC 就使用聚合设备
            device_index=device_index
        )

        # 初始化打断控制器
        self.interrupt_controller = InterruptController()

        # 初始化 TTS 客户端（全局复用，初始化时创建一次）
        volc_cfg = self.llm_tts.config.get("volcengine_seed2", {})
        volc_app_id = volc_cfg.get("app_id")
        volc_token = volc_cfg.get("access_token") or volc_cfg.get("api_key")

        if volc_app_id and volc_token:
            self.realtime_tts = VolcengineRealtimeTTS(
                app_id=volc_app_id,
                access_token=volc_token,
                voice="zh_female_cancan_mars_bigtts"
            )
            print('🔊 TTS: volcengine_seed2')
        else:
            # 默认回退到 Qwen3 TTS（使用同一个 DashScope Key）
            self.realtime_tts = Qwen3RealtimeTTS(
                api_key=api_key,
                voice="Cherry",
                verbose=False
            )
            print('🔊 TTS: qwen3')

        # 状态
        self.is_listening = False
        self.is_tts_playing = False
        self.current_text = ""
        self.current_pipeline = None  # 当前正在运行的 pipeline
        self.current_player = None    # 当前正在播放的 player
        self.current_tts_thread = None  # 当前 TTS 线程
        self.last_sentence_time = 0  # 上次触发对话的时间（防止太快重复触发）
        self.should_exit = False  # 退出标志

    def on_asr_text(self, text: str):
        """ASR 中间结果回调"""
        # 如果 AI 正在说话，只用于打断检测，不显示
        if self.is_tts_playing:
            self.interrupt_controller.on_asr_text(text, is_final=False)
            return

        self.current_text = text
        print(f'\r💬 {text}', end='', flush=True)

    def on_asr_sentence(self, text: str):
        """ASR 完整句子回调"""
        # 过滤空文本和太短的文本（避免噪音触发）
        if not text or not text.strip() or len(text.strip()) < 2:
            return

        # 检查退出命令
        exit_keywords = ['退出', '再见', '拜拜', '结束对话', '关闭程序']
        if any(keyword in text.strip() for keyword in exit_keywords):
            print(f'\n\n👋 检测到退出命令: "{text}"')
            print('正在退出程序...')
            # 设置退出标志
            self.should_exit = True
            return

        # 如果 AI 正在说话，检查是否是真实打断
        # 优化：降低阈值到 4 个字符，提高打断响应速度
        if self.is_tts_playing:
            text_length = len(text.strip())
            # 过滤太短的文本（< 3 个字符）和常见回声词
            if text_length < 3:
                print(f'\n⚠️ 忽略短文本（可能是回声）: "{text}" (长度: {text_length})')
                return

            # 检查是否是单个回声词（1-2 个字符的常见词）
            echo_keywords = ['嗯', '啊', '哦', '呃', '嗯嗯', '啊啊', '哦哦']
            if text.strip() in echo_keywords:
                print(f'\n⚠️ 忽略回声关键词: "{text}"')
                return

            # 3 个字符以上的文本认为是真实打断
            print(f'\n🔔 检测到打断: "{text}" (长度: {text_length})')

        # 防止说话太快时重复触发（间隔少于1秒的忽略）
        current_time = time.time()
        if current_time - self.last_sentence_time < 1.0 and not self.is_tts_playing:
            return
        self.last_sentence_time = current_time

        # 如果正在播放，直接打断并清空（不等待）
        if self.is_tts_playing:
            self.on_interrupt()
            # 不等待旧线程，直接继续（打断就是打断，不管旧的了）

        print(f'\n\n👤 你: {text}')
        self.current_text = ""

        # 停止监听
        self.is_listening = False

        # 在新线程中处理 LLM + TTS，避免阻塞 ASR
        tts_thread = threading.Thread(target=self._process_and_speak, args=(text,))
        tts_thread.daemon = True
        tts_thread.start()
        self.current_tts_thread = tts_thread

    def _process_and_speak(self, text: str):
        """在单独线程中处理 LLM + TTS（使用两阶段结构化输出记忆方案）"""
        try:
            # 发送给 LLM 并播放回复
            self.is_tts_playing = True

            # 启动打断监听（在 TTS 播放时）
            self.interrupt_controller.set_tts_speaking(True)

            # 获取对话历史
            history = []
            for msg in self.llm_tts.voice_prompt.conversation_history:
                history.append(msg)

            # 复用全局 TTS 客户端（不再每次创建新的）
            streaming_player = PyAudioStreamPlayer(
                sample_rate=24000
            )

            # 创建实时管道
            pipeline = RealtimeStreamingPipeline()

            # 保存引用以便打断
            self.current_pipeline = pipeline
            self.current_player = streaming_player

            # 使用 MemoryEnhancedChat 的流式输出（两阶段记忆管理）
            def llm_stream_generator():
                """将 MemoryEnhancedChat.chat_stream 转换为 pipeline 需要的格式"""
                for chunk in self.llm_tts.memory_chat.chat_stream(text, history):
                    yield chunk

            # 运行实时管道（复用全局 TTS 客户端）
            result = pipeline.run(
                llm_stream=llm_stream_generator(),
                realtime_tts_client=self.realtime_tts,
                streaming_player=streaming_player,
                display_text=True
            )

            # 保存对话历史（即使被打断也要保存，因为 LLM 已经生成了回复）
            if result and result.get("text"):
                self.llm_tts.voice_prompt.add_conversation('user', text)
                self.llm_tts.voice_prompt.add_conversation('assistant', result["text"])

        except Exception as e:
            print(f'\n❌ 错误: {e}')

        finally:
            # 清除引用
            self.current_pipeline = None
            self.current_player = None

            # TTS 播放完成
            self.is_tts_playing = False
            self.interrupt_controller.set_tts_speaking(False)

            # 重新开始监听
            self.is_listening = True
            print('\n')

    def on_interrupt(self):
        """打断回调"""
        # 停止 TTS 管道
        if self.current_pipeline:
            self.current_pipeline.stop()

        # 立即结束旧 session（火山引擎限制同时只能有1个session）
        if hasattr(self, 'realtime_tts'):
            if hasattr(self.realtime_tts, 'finish'):
                self.realtime_tts.finish()
            if hasattr(self.realtime_tts, 'clear_queue'):
                self.realtime_tts.clear_queue()

        # 停止音频播放
        if self.current_player:
            self.current_player.stop()

        self.is_tts_playing = False

    def start(self):
        """启动语音交互"""
        print('\n🎙️  导师评价学姐助手 - 语音交互模式')
        if self.enable_aec:
            print('🎛️  AEC 回声消除已启用')
        print('━' * 50)
        print('💡 退出方式：')
        print('   1. 说"退出"、"再见"、"拜拜"等退出命令')
        print('   2. 按 Ctrl+C 强制退出')
        print('━' * 50)
        print()

        try:
            # 启动音频输入（先启动，确保麦克风打开）
            self.audio_input.start(audio_callback=self.asr.send_audio)

            # 启动 ASR（同步启动，确保鉴权失败等错误能立刻暴露）
            self.asr.start(
                on_text=self.on_asr_text,
                on_sentence=self.on_asr_sentence
            )
            time.sleep(0.2)

            # 启动打断控制器
            self.interrupt_controller.start_monitoring(
                interrupt_callback=self.on_interrupt
            )

            self.is_listening = True
            print('🎤 请说话...\n')

            # 持续运行，检查退出标志
            while not self.should_exit:
                time.sleep(0.1)

            # 正常退出
            print('\n👋 再见!')

        except KeyboardInterrupt:
            print('\n\n👋 再见!')

        finally:
            # 清理资源
            self.audio_input.stop()
            self.asr.stop()
            self.audio_input.close()
            self.interrupt_controller.stop_monitoring()

            # 关闭 AEC 处理器
            if self.aec_processor:
                self.aec_processor.close()

            # 断开 TTS 连接（复用的全局客户端）
            if hasattr(self, 'realtime_tts'):
                if hasattr(self.realtime_tts, 'disconnect'):
                    self.realtime_tts.disconnect()

            # 关闭 Mem0 连接，确保数据持久化
            if self.llm_tts.mem0_manager:
                self.llm_tts.mem0_manager.close()


def load_env_file():
    """手动加载 .env 文件"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def _mask_secret(value: str, show_last: int = 4) -> str:
    """Mask secrets for logs (avoid leaking full keys)."""
    if not value:
        return ""
    value = str(value).strip()
    if len(value) <= show_last:
        return "*" * len(value)
    return "*" * (len(value) - show_last) + value[-show_last:]


def check_asr_auth(asr_model: str = "paraformer-realtime-v2") -> int:
    """Quickly validate DashScope ASR auth without opening microphone."""
    env_vars = load_env_file()
    api_key = (
        env_vars.get('QWEN3_API_KEY') or os.getenv('QWEN3_API_KEY') or
        env_vars.get('DASHSCOPE_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
    )

    if not api_key:
        print('❌ 未找到 DashScope API Key（QWEN3_API_KEY 或 DASHSCOPE_API_KEY）')
        return 2

    print(f"🔑 DashScope Key: {_mask_secret(api_key)}")
    print(f"🎤 ASR 模型: {asr_model}")

    asr = DashScopeASR(api_key=api_key, model=asr_model)
    try:
        asr.start(on_text=lambda _: None, on_sentence=lambda _: None)
        # 立即停止，只验证鉴权/连接是否成功
        asr.stop()
        print('✅ ASR 鉴权/连接正常')
        return 0
    except Exception as e:
        print(f'❌ ASR 鉴权/连接失败: {e}')
        return 1


def list_audio_devices():
    """列出所有音频设备"""
    import pyaudio
    p = pyaudio.PyAudio()
    print("\n可用的音频输入设备：")
    print("=" * 80)
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"\n设备 {i}: {info['name']}")
            print(f"  输入通道数: {info['maxInputChannels']}")
            print(f"  采样率: {int(info['defaultSampleRate'])} Hz")
            if 'Aggregate' in info['name'] or 'aggregate' in info['name'].lower():
                print("  ⭐ 这是聚合设备！")
    print("=" * 80)
    print("\n使用方法：")
    print("  1. 禁用 AEC（耳机模式）：python -m src.main --voice --no-aec")
    print("  2. 启用 AEC（外放模式）：python -m src.main --voice --device-index <聚合设备索引>")
    p.terminate()


class LLMTTSTest:
    def __init__(self, config_path: str = "config/api_keys.json", role_config: dict = None):
        """
        初始化测试类

        Args:
            config_path: 配置文件路径
            role_config: 角色配置（从 role_loader 加载）
        """
        # 使用新的配置加载器
        config_loader = ConfigLoader()
        self.config = config_loader.get_config()

        # 静默打印配置状态
        # config_loader.print_status()

        self.llm_client = None
        self.output_dir = "data/audios"

        # 初始化 Mem0 记忆管理器
        mem0_config = self.config.get("mem0", {})
        self.mem0_manager = None
        if mem0_config.get("enable_mem0", False):
            self.mem0_manager = Mem0Manager(mem0_config)

        # 用户ID（从配置获取）
        self.user_id = mem0_config.get("user_id", "default_user")

        # 角色描述（用于记忆增强对话）
        self.role_description = "你是一个友好的语音助手，说话简洁自然"
        if role_config:
            self.role_description = f"你是{role_config.get('name', '助手')}，{role_config.get('personality', '友好')}"

        # 初始化记忆增强对话（新方案：两阶段结构化输出）
        llm_config = self.config.get("openai_compatible", {})
        self.memory_chat = MemoryEnhancedChat(
            api_key=llm_config.get("api_key"),
            base_url=llm_config.get("base_url"),
            model=llm_config.get("model", "qwen3-max"),
            mem0_manager=self.mem0_manager,
            user_id=self.user_id,
            role_description=self.role_description,
            verbose=False  # 生产模式关闭详细日志
        )

        # 初始化语音助手 Prompt 管理器（保留用于对话历史管理）
        self.voice_prompt = VoiceAssistantPrompt(role_config=role_config, mem0_manager=None)

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def initialize_llm(self):
        """初始化LLM客户端"""
        llm_config = self.config.get("openai_compatible", {})
        self.llm_client = LLMClient(
            api_key=llm_config.get("api_key"),
            base_url=llm_config.get("base_url"),
            model=llm_config.get("model")
        )
        # print(f"✓ LLM客户端初始化完成: {self.llm_client.get_model_info()}")  # 静默初始化

    def chat_and_speak_realtime(self, prompt: str, play_audio: bool = True):
        """
        真正的实时对话（两阶段结构化输出记忆方案）
        第一阶段：分析意图，检索/存储记忆
        第二阶段：流式生成回复 → 实时 TTS → 流式播放

        Args:
            prompt: 用户输入
            play_audio: 是否播放音频
        """
        # 获取对话历史
        history = []
        for msg in self.voice_prompt.conversation_history:
            history.append(msg)

        # 创建实时 TTS 客户端
        config = self.config.get("qwen3_tts", {})
        realtime_tts = Qwen3RealtimeTTS(
            api_key=config.get("api_key"),
            voice="Cherry",
            verbose=False  # 关闭 TTS 日志
        )

        # 创建流式播放器 - PyAudio
        streaming_player = PyAudioStreamPlayer(sample_rate=24000)

        # 创建实时管道
        pipeline = RealtimeStreamingPipeline()

        # 使用 MemoryEnhancedChat 的流式输出（两阶段记忆管理）
        def llm_stream_generator():
            """将 MemoryEnhancedChat.chat_stream 转换为 pipeline 需要的格式"""
            for chunk in self.memory_chat.chat_stream(prompt, history):
                yield chunk

        # 运行实时管道
        result = pipeline.run(
            llm_stream=llm_stream_generator(),
            realtime_tts_client=realtime_tts,
            streaming_player=streaming_player,
            display_text=True
        )

        # 保存对话历史（短期记忆）
        self.voice_prompt.add_conversation('user', prompt)
        self.voice_prompt.add_conversation('assistant', result["text"])

        print()  # 换行

        return {
            "prompt": prompt,
            "response": result["text"],
            "mode": "realtime",
            "metrics": result["metrics"]
        }

    def chat_and_speak_realtime_volcengine(self, prompt: str, play_audio: bool = True):
        """
        火山引擎实时对话（两阶段结构化输出记忆方案）
        第一阶段：分析意图，检索/存储记忆
        第二阶段：流式生成回复 → 实时 TTS → 流式播放

        Args:
            prompt: 用户输入
            play_audio: 是否播放音频
        """
        # 获取对话历史
        history = []
        for msg in self.voice_prompt.conversation_history:
            history.append(msg)

        # 创建实时 TTS 客户端
        config = self.config.get("volcengine_seed2", {})
        realtime_tts = VolcengineRealtimeTTS(
            app_id=config.get("app_id"),
            access_token=config.get("access_token") or config.get("api_key"),
            voice="zh_female_cancan_mars_bigtts"
        )

        # 创建流式播放器 - PyAudio
        streaming_player = PyAudioStreamPlayer(sample_rate=24000)

        # 创建实时管道
        pipeline = RealtimeStreamingPipeline()

        # 使用 MemoryEnhancedChat 的流式输出（两阶段记忆管理）
        def llm_stream_generator():
            """将 MemoryEnhancedChat.chat_stream 转换为 pipeline 需要的格式"""
            for chunk in self.memory_chat.chat_stream(prompt, history):
                yield chunk

        # 运行实时管道
        result = pipeline.run(
            llm_stream=llm_stream_generator(),
            realtime_tts_client=realtime_tts,
            streaming_player=streaming_player,
            display_text=True
        )

        # 保存对话历史（短期记忆）
        self.voice_prompt.add_conversation('user', prompt)
        self.voice_prompt.add_conversation('assistant', result["text"])

        print()  # 换行

        return {
            "prompt": prompt,
            "response": result["text"],
            "mode": "realtime_volcengine",
            "metrics": result["metrics"]
        }

    def interactive_mode(self, use_realtime: bool = True):
        """
        交互式对话模式

        Args:
            use_realtime: 是否使用实时模式（默认开启）
        """
        print("\n" + "="*60)
        print("🎙️  语音助手交互模式")
        print("="*60)
        print("\n命令:")
        print("  /quit      - 退出")
        print("  /provider  - 切换 TTS 提供商")
        print("  /role      - 切换角色")
        print("  /clear     - 清空对话历史")
        print("  /memories  - 查看长期记忆")
        print("  /clearmem  - 清除长期记忆")
        print("  /user <ID> - 切换用户")
        print()

        current_provider = "qwen3"

        provider_desc = {
            "qwen3": "通义千问 TTS",
            "volcengine": "火山引擎 TTS"
        }

        print(f"当前 TTS: {provider_desc[current_provider]}")
        if self.mem0_manager and self.mem0_manager.enabled:
            print(f"记忆功能: ✅ 已启用 (用户: {self.user_id})")
        else:
            print(f"记忆功能: ❌ 未启用")
        print()

        while True:
            try:
                user_input = input("💬 你: ").strip()

                if not user_input:
                    continue

                if user_input == "/quit":
                    print("\n👋 再见!")
                    break

                elif user_input == "/help":
                    print("\n📖 可用命令:")
                    print("  /quit      - 退出程序")
                    print("  /provider  - 切换 TTS 提供商 (qwen3/volcengine)")
                    print("  /role      - 切换角色")
                    print("  /clear     - 清空对话历史")
                    print("  /history   - 查看对话历史")
                    print("  /memories  - 查看长期记忆")
                    print("  /clearmem  - 清除长期记忆")
                    print("  /user <ID> - 切换用户")
                    print("  /info      - 查看当前配置")
                    print("  /help      - 显示此帮助信息")
                    print()

                elif user_input == "/provider":
                    # 循环切换 TTS 提供商
                    providers = ["qwen3", "volcengine"]
                    current_idx = providers.index(current_provider)
                    current_provider = providers[(current_idx + 1) % len(providers)]
                    print(f"✓ 已切换到: {provider_desc[current_provider]}\n")

                elif user_input == "/clear":
                    self.voice_prompt.clear_history()
                    print("✓ 对话历史已清空\n")

                elif user_input.startswith("/role"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        role = parts[1]
                        try:
                            self.voice_prompt.set_role(role)
                            role_info = self.voice_prompt.get_role_info()
                            print(f"✓ 已切换到角色: {role_info['name']}\n")
                        except ValueError as e:
                            print(f"❌ {str(e)}\n")
                    else:
                        current_role = self.voice_prompt.get_role_info()
                        print(f"当前角色: {current_role['name']}")
                        print("可选角色: default, casual, professional, companion\n")

                elif user_input == "/history":
                    summary = self.voice_prompt.get_conversation_summary()
                    print(f"\n对话历史:\n{summary}\n")

                elif user_input.startswith("/setname"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        name = parts[1]
                        self.voice_prompt.set_user_info(name=name)
                        print(f"✓ 用户名已设置为: {name}\n")
                    else:
                        print("❌ 请提供用户名，例如: /setname 小明\n")

                elif user_input.startswith("/addknowledge"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        knowledge = parts[1]
                        self.voice_prompt.add_knowledge(knowledge)
                        print(f"✓ 已添加知识: {knowledge}\n")
                    else:
                        print("❌ 请提供知识内容，例如: /addknowledge 用户喜欢攀岩\n")

                elif user_input == "/memories":
                    # 查看长期记忆
                    if self.mem0_manager and self.mem0_manager.enabled:
                        memories = self.mem0_manager.get_all_memories(self.user_id)
                        if memories:
                            print(f"\n📝 长期记忆 (用户: {self.user_id}):")
                            for i, mem in enumerate(memories, 1):
                                print(f"  {i}. {mem['memory']}")
                            print()
                        else:
                            print("暂无长期记忆\n")
                    else:
                        print("❌ Mem0 未启用\n")

                elif user_input == "/clearmem":
                    # 清除长期记忆
                    if self.mem0_manager and self.mem0_manager.enabled:
                        self.mem0_manager.clear_memories(self.user_id)
                        print(f"✓ 已清除用户 {self.user_id} 的所有记忆\n")
                    else:
                        print("❌ Mem0 未启用\n")

                elif user_input.startswith("/user"):
                    # 切换用户
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        self.user_id = parts[1]
                        # 更新 memory_chat 的 user_id
                        self.memory_chat.user_id = self.user_id
                        print(f"✓ 已切换到用户: {self.user_id}\n")
                    else:
                        print(f"当前用户: {self.user_id}\n")

                elif user_input == "/info":
                    role_info = self.voice_prompt.get_role_info()
                    print("\n当前配置:")
                    print(f"  TTS 提供商: {provider_desc[current_provider]}")
                    print(f"  角色: {role_info['name']} ({role_info['personality']})")
                    print(f"  对话轮数: {len(self.voice_prompt.conversation_history) // 2}")
                    print(f"  知识库条目: {len(self.voice_prompt.knowledge_base)}")
                    if self.mem0_manager and self.mem0_manager.enabled:
                        mem_count = len(self.mem0_manager.get_all_memories(self.user_id))
                        print(f"  长期记忆: {mem_count} 条 (用户: {self.user_id})")
                    print()

                else:
                    # 实时对话
                    if current_provider == "qwen3":
                        self.chat_and_speak_realtime(user_input)
                    elif current_provider == "volcengine":
                        self.chat_and_speak_realtime_volcengine(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 再见!")
                # 确保正确关闭 Mem0 连接
                if self.mem0_manager and self.mem0_manager.enabled:
                    self.mem0_manager.close()
                break
            except Exception as e:
                print(f"\n❌ 错误: {str(e)}\n")

        # 正常退出时也要关闭连接
        if self.mem0_manager and self.mem0_manager.enabled:
            self.mem0_manager.close()


def main():
    """主函数 - 支持多种运行模式"""
    parser = argparse.ArgumentParser(
        description='Personality TTS - 个性化语音助手',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式：
  文字对话模式（默认）：
    python -m src.main
    python -m src.main --text

  语音对话模式：
    python -m src.main --voice --no-aec           # 耳机模式（推荐）
    python -m src.main --voice --device-index <N> # AEC 模式

  其他工具：
    python -m src.main --list-devices             # 列出音频设备
    python -m src.main --check-asr                # 检查 ASR 鉴权
        """
    )

    # 运行模式
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--text', action='store_true', help='文字对话模式（你打字，AI 说话）')
    mode_group.add_argument('--voice', action='store_true', help='语音对话模式（你说话，AI 说话）')

    # 语音模式参数
    parser.add_argument('--no-aec', action='store_true', help='禁用 AEC（回声消除），使用耳机模式')
    parser.add_argument('--device-index', type=int, help='聚合设备索引（启用 AEC 时必须提供）')
    parser.add_argument('--asr-model', type=str, default='paraformer-realtime-v2',
                        choices=['paraformer-realtime-v2', 'fun-asr-realtime-2025-11-07'],
                        help='ASR 模型选择（默认: paraformer-realtime-v2）')

    # 工具命令
    parser.add_argument('--check-asr', action='store_true', help='仅检查 ASR 鉴权/连接（不打开麦克风）')
    parser.add_argument('--list-devices', action='store_true', help='列出所有音频设备')

    # 角色选择
    parser.add_argument('--role', type=str, help='指定角色（如: natural, xuejie, funny 等）')

    args = parser.parse_args()

    # 工具命令优先处理
    if args.list_devices:
        list_audio_devices()
        return

    if args.check_asr:
        raise SystemExit(check_asr_auth(asr_model=args.asr_model))

    # 确定运行模式（默认为文字对话模式）
    if args.voice:
        # 语音对话模式
        try:
            # 加载角色配置
            role_loader = RoleLoader()
            role_config = None
            if args.role:
                role_config = role_loader.get_role(args.role)
                if role_config:
                    print(f"\n✓ 使用角色: {role_config['name']}")
                    print(f"  特点: {role_config['personality']}")
                    print(f"  风格: {role_config['style']}\n")
            else:
                # 默认使用 xuejie 角色
                role_config = role_loader.get_role("xuejie")

            voice_mode = VoiceInteractiveMode(
                enable_aec=not args.no_aec,
                device_index=args.device_index,
                asr_model=args.asr_model,
                role_config=role_config
            )
            voice_mode.start()
        except Exception as e:
            print(f'错误: {e}')
            import traceback
            traceback.print_exc()
    else:
        # 文字对话模式（默认）
        print('\n' + '='*60)
        print('💬 文字对话模式')
        print('='*60)
        print('\n✨ 支持智能记忆功能')
        print('   - LLM 会自动保存重要信息')
        print('   - 使用 /memories 查看记忆')
        print('   - 使用 /help 查看所有命令\n')

        # 加载角色
        role_loader = RoleLoader()

        # 如果指定了角色，使用指定角色；否则让用户选择
        if args.role:
            role_config = role_loader.get_role(args.role)
            if role_config:
                print(f"✓ 使用角色: {role_config['name']}")
                print(f"  特点: {role_config['personality']}")
                print(f"  风格: {role_config['style']}\n")
            else:
                print(f"⚠️ 未找到角色 '{args.role}'，使用默认角色")
                role_config = role_loader.get_role("natural")
        else:
            # 让用户选择角色
            selected_role_id = role_loader.select_role_interactive()
            if selected_role_id:
                role_config = role_loader.get_role(selected_role_id)
                print(f"\n✓ 使用角色: {role_config['name']}")
                print(f"  特点: {role_config['personality']}")
                print(f"  风格: {role_config['style']}\n")
            else:
                # 默认使用 natural 角色
                role_config = role_loader.get_role("natural")

        print(f"正在初始化...")

        # 初始化
        test = LLMTTSTest(role_config=role_config)
        test.initialize_llm()

        print("✓ 初始化完成\n")

        # 进入交互模式（使用实时模式）
        test.interactive_mode(use_realtime=True)


if __name__ == "__main__":
    main()
