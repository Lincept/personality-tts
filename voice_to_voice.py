"""
ASR 集成示例 - 将语音识别集成到主程序
支持 AEC（回声消除）功能
"""
import os
import sys
import time
from typing import Optional


# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.asr import DashScopeASR, AudioInput, InterruptController
from src.asr.aec_processor import SimpleAEC
from src.main import LLMTTSTest
from src.role_loader import RoleLoader
from src.config_loader import ConfigLoader


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
    config = ConfigLoader().get_config()
    api_key = config.get("qwen3_tts", {}).get("api_key")

    if not api_key:
        print('❌ 未找到 DashScope API Key，请在 config/api_keys.json 中配置 qwen3_tts.api_key')
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


class VoiceInteractiveMode:
    """语音交互模式 - 支持语音输入和打断，集成 AEC 回声消除"""

    def __init__(self, enable_aec: bool = True, device_index: Optional[int] = None, asr_model: str = "paraformer-realtime-v2"):
        """
        初始化语音交互模式

        Args:
            enable_aec: 是否启用 AEC（回声消除）- 需要配置聚合设备
            device_index: 音频设备索引（聚合设备的索引，启用 AEC 时必须提供）
            asr_model: ASR 模型选择
                - "paraformer-realtime-v2": Paraformer 实时模型 v2（推荐，准确度高）
                - "fun-asr-realtime-2025-11-07": FunASR 2025 版本（默认）
        """
        # 使用 ConfigLoader 统一加载配置
        self.config = ConfigLoader().get_config()
        api_key = self.config.get("qwen3_tts", {}).get("api_key")

        if not api_key:
            raise ValueError(
                '未找到 DashScope API Key，请在 config/api_keys.json 中配置 qwen3_tts.api_key'
            )

        # 仅展示脱敏信息，方便排查是否读取到了 Key
        print(f"🔑 DashScope Key: {_mask_secret(api_key)}")

        # 加载角色配置
        role_loader = RoleLoader()
        role_config = role_loader.get_role("xuejie")  # 使用学姐助手角色

        # 初始化主程序
        self.llm_tts = LLMTTSTest(role_config=role_config)

        # 提前校验 LLM 配置，避免进入语音流程后才 401
        llm_cfg = self.llm_tts.config.get("openai_compatible", {})
        if not llm_cfg.get("api_key"):
            raise ValueError(
                '未找到 LLM 的 API Key，请在 config/api_keys.json 中配置 openai_compatible.api_key'
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
                    '请先运行: python voice_to_voice.py --list-devices\n'
                    '然后使用: python voice_to_voice.py --device-index <索引>'
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

        # 初始化 TTS 客户端（默认使用 Qwen3 TTS，可选火山引擎）
        volc_cfg = self.llm_tts.config.get("volcengine_seed2", {})
        volc_app_id = volc_cfg.get("app_id")
        volc_token = volc_cfg.get("access_token") or volc_cfg.get("api_key")

        # 只有明确配置了火山引擎才使用，否则默认 Qwen3 TTS
        if volc_app_id and volc_token:
            from src.tts.volcengine_realtime_tts import VolcengineRealtimeTTS
            self.realtime_tts = VolcengineRealtimeTTS(
                app_id=volc_app_id,
                access_token=volc_token,
                voice="zh_female_cancan_mars_bigtts"
            )
            print('🔊 TTS: volcengine_seed2')
        else:
            from src.tts.qwen3_realtime_tts import Qwen3RealtimeTTS
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
        import threading
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
            from src.audio.pyaudio_player import PyAudioStreamPlayer
            from src.realtime_pipeline import RealtimeStreamingPipeline

            # 创建流式播放器（每次创建新的，避免状态冲突）
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


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='语音交互模式 - 支持 AEC 回声消除（需要聚合设备 + BlackHole）')
    parser.add_argument('--no-aec', action='store_true', help='禁用 AEC（回声消除），使用耳机模式')
    parser.add_argument('--device-index', type=int, help='聚合设备索引（启用 AEC 时必须提供）')
    parser.add_argument('--asr-model', type=str, default='paraformer-realtime-v2',
                        choices=['paraformer-realtime-v2', 'fun-asr-realtime-2025-11-07'],
                        help='ASR 模型选择（默认: paraformer-realtime-v2）')
    parser.add_argument('--check-asr', action='store_true', help='仅检查 ASR 鉴权/连接（不打开麦克风）')
    parser.add_argument('--list-devices', action='store_true', help='列出所有音频设备')
    args = parser.parse_args()

    # 如果用户要求列出设备
    if args.list_devices:
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
        print("  1. 禁用 AEC（耳机模式）：python voice_to_voice.py --no-aec")
        print("  2. 启用 AEC（外放模式）：python voice_to_voice.py --device-index <聚合设备索引>")
        p.terminate()
        return

    if args.check_asr:
        raise SystemExit(check_asr_auth(asr_model=args.asr_model))

    try:
        voice_mode = VoiceInteractiveMode(
            enable_aec=not args.no_aec,
            device_index=args.device_index,
            asr_model=args.asr_model
        )
        voice_mode.start()
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
