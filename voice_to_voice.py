"""
ASR 集成示例 - 将语音识别集成到主程序
"""
import os
import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.asr import DashScopeASR, AudioInput, InterruptController
from src.main import LLMTTSTest
from src.role_loader import RoleLoader


def load_env_file():
    """手动加载 .env 文件"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


class VoiceInteractiveMode:
    """语音交互模式 - 支持语音输入和打断"""

    def __init__(self):
        """初始化语音交互模式"""
        # 加载环境变量
        env_vars = load_env_file()
        api_key = env_vars.get('QWEN3_API_KEY') or os.getenv('QWEN3_API_KEY')

        if not api_key:
            raise ValueError('未找到 QWEN3_API_KEY，请检查 .env 文件')

        # 加载角色配置
        role_loader = RoleLoader()
        role_config = role_loader.get_role("default")

        # 初始化主程序
        self.llm_tts = LLMTTSTest(role_config=role_config)
        self.llm_tts.initialize_llm()

        # 初始化 ASR
        self.asr = DashScopeASR(api_key=api_key)

        # 初始化音频输入
        self.audio_input = AudioInput(sample_rate=16000, chunk_size=1600)

        # 初始化打断控制器
        self.interrupt_controller = InterruptController()

        # 状态
        self.is_listening = False
        self.is_tts_playing = False
        self.current_text = ""
        self.current_pipeline = None  # 当前正在运行的 pipeline
        self.current_player = None    # 当前正在播放的 player

    def on_asr_text(self, text: str):
        """ASR 中间结果回调"""
        self.current_text = text
        print(f'\r[识别中] {text}', end='', flush=True)

        # 如果 TTS 正在播放，检测打断
        if self.is_tts_playing:
            self.interrupt_controller.on_asr_text(text, is_final=False)

    def on_asr_sentence(self, text: str):
        """ASR 完整句子回调"""
        # 如果正在播放，说明这是打断后的新输入，忽略之前的对话
        if self.is_tts_playing:
            print(f'\n[打断] 检测到新输入，取消当前回复')
            self.on_interrupt()
            # 等待旧的 TTS 线程完全停止（减少等待时间）
            time.sleep(0.3)

        print(f'\n[你说] {text}')
        self.current_text = ""

        # 停止监听
        self.is_listening = False

        # 在新线程中处理 LLM + TTS，避免阻塞 ASR
        import threading
        tts_thread = threading.Thread(target=self._process_and_speak, args=(text,))
        tts_thread.daemon = True
        tts_thread.start()

    def _process_and_speak(self, text: str):
        """在单独线程中处理 LLM + TTS"""
        try:
            # 发送给 LLM 并播放回复
            print('[AI 思考中...]')
            self.is_tts_playing = True

            # 启动打断监听（在 TTS 播放时）
            self.interrupt_controller.set_tts_speaking(True)

            # 获取 LLM 消息
            messages = self.llm_tts.voice_prompt.get_messages(text, user_id=self.llm_tts.user_id)

            # 创建实时 TTS 客户端
            from src.tts.qwen3_realtime_tts import Qwen3RealtimeTTS
            from src.audio.pyaudio_player import PyAudioStreamPlayer
            from src.realtime_pipeline import RealtimeStreamingPipeline

            config = self.llm_tts.config.get("qwen3_tts", {})
            realtime_tts = Qwen3RealtimeTTS(
                api_key=config.get("api_key"),
                voice="Cherry"
            )

            # 创建流式播放器
            streaming_player = PyAudioStreamPlayer(sample_rate=24000)

            # 创建实时管道
            pipeline = RealtimeStreamingPipeline()

            # 保存引用以便打断
            self.current_pipeline = pipeline
            self.current_player = streaming_player

            # 获取 LLM 流式输出
            llm_stream = self.llm_tts.llm_client.chat_stream(
                messages=messages,
                temperature=self.llm_tts.test_config["llm_config"]["temperature"]
            )

            # 运行实时管道
            result = pipeline.run(
                llm_stream=llm_stream,
                realtime_tts_client=realtime_tts,
                streaming_player=streaming_player,
                display_text=True
            )

            # 检查是否被打断
            if pipeline.stop_event.is_set():
                print('\n[打断] 播放已停止')
                return

            # 保存对话历史
            self.llm_tts.voice_prompt.add_conversation('user', text)
            self.llm_tts.voice_prompt.add_conversation('assistant', result["text"])

            # 保存到 Mem0
            if self.llm_tts.mem0_manager:
                self.llm_tts.mem0_manager.add_conversation(
                    user_input=text,
                    assistant_response=result["text"],
                    user_id=self.llm_tts.user_id
                )

            print("\n✓ 实时流式处理完成")

        except Exception as e:
            print(f'\n[错误] TTS 处理失败: {e}')
            import traceback
            traceback.print_exc()

        finally:
            # 清除引用
            self.current_pipeline = None
            self.current_player = None

            # TTS 播放完成
            self.is_tts_playing = False
            self.interrupt_controller.set_tts_speaking(False)

            # 重新开始监听
            self.is_listening = True
            print('\n[等待你说话...]')

    def on_interrupt(self):
        """打断回调"""
        print('\n[打断] 检测到你在说话，停止播放')

        # 停止 TTS 管道
        if self.current_pipeline:
            self.current_pipeline.stop()
            print('[打断] 已停止 TTS 管道')

        # 停止音频播放
        if self.current_player:
            self.current_player.stop()
            print('[打断] 已停止音频播放')

        self.is_tts_playing = False

    def start(self):
        """启动语音交互"""
        print('\n' + '='*60)
        print('🎙️  语音交互模式')
        print('='*60)
        print('\n功能:')
        print('  - 实时语音识别 (ASR)')
        print('  - 语音打断 (Barge-in)')
        print('  - 实时语音合成 (TTS)')
        print('\n按 Ctrl+C 退出\n')

        try:
            # 启动 ASR
            print('启动语音识别...')
            self.asr.start(
                on_text=self.on_asr_text,
                on_sentence=self.on_asr_sentence
            )
            time.sleep(1)

            # 启动音频输入
            print('启动麦克风录音...')
            self.audio_input.start(audio_callback=self.asr.send_audio)

            # 启动打断控制器
            self.interrupt_controller.start_monitoring(
                interrupt_callback=self.on_interrupt
            )

            self.is_listening = True
            print('\n[等待你说话...]')

            # 持续运行
            while True:
                time.sleep(0.1)

        except KeyboardInterrupt:
            print('\n\n退出中...')

        finally:
            # 清理资源
            print('清理资源...')
            self.audio_input.stop()
            self.asr.stop()
            self.audio_input.close()
            self.interrupt_controller.stop_monitoring()
            print('再见!')


def main():
    """主函数"""
    try:
        voice_mode = VoiceInteractiveMode()
        voice_mode.start()
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
