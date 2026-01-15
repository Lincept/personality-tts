"""
Qwen3 实时 TTS 客户端 - 支持流式文本输入和流式音频输出
使用 WebSocket 连接，真正的实时语音合成
"""
import os
import base64
import threading
import queue
import time
import dashscope
from dashscope.audio.qwen_tts_realtime import (
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
    AudioFormat
)


class RealtimeTTSCallback(QwenTtsRealtimeCallback):
    """实时 TTS 回调处理器"""

    def __init__(self, audio_queue: queue.Queue, verbose: bool = False):
        """
        Args:
            audio_queue: 音频数据队列，用于传递给播放器
            verbose: 是否显示详细日志
        """
        self.audio_queue = audio_queue
        self.complete_event = threading.Event()
        self.session_id = None
        self.first_audio_received = False
        self.start_time = None
        self.verbose = verbose

    def on_open(self) -> None:
        """连接建立"""
        if self.verbose:
            print('[实时TTS] WebSocket 连接已建立')
        self.start_time = time.time()

    def on_close(self, close_status_code, close_msg) -> None:
        """连接关闭"""
        if self.verbose:
            print(f'[实时TTS] 连接关闭: code={close_status_code}, msg={close_msg}')
        self.audio_queue.put(None)  # 结束信号

    def on_event(self, response: dict) -> None:
        """处理服务端事件"""
        try:
            event_type = response.get('type')

            if event_type == 'session.created':
                self.session_id = response['session']['id']
                if self.verbose:
                    print(f'[实时TTS] 会话创建: {self.session_id}')

            elif event_type == 'response.audio.delta':
                # 接收音频数据块
                audio_b64 = response.get('delta', '')
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    self.audio_queue.put(audio_bytes)

                    if not self.first_audio_received:
                        self.first_audio_received = True
                        if self.verbose:
                            delay = time.time() - self.start_time
                            print(f'[实时TTS] 首个音频块延迟: {delay:.3f}秒')

            elif event_type == 'response.done':
                if self.verbose:
                    response_id = response.get('response', {}).get('id', 'unknown')
                    print(f'[实时TTS] 响应完成: {response_id}')

            elif event_type == 'session.finished':
                if self.verbose:
                    print('[实时TTS] 会话结束')
                self.complete_event.set()

            elif event_type == 'error':
                error = response.get('error', {})
                print(f'[实时TTS] 错误: {error}')

        except Exception as e:
            if self.verbose:
                print(f'[实时TTS] 事件处理错误: {e}')

    def wait_for_finished(self, timeout=None):
        """等待会话完成"""
        return self.complete_event.wait(timeout)


class Qwen3RealtimeTTS:
    """Qwen3 实时 TTS 客户端"""

    def __init__(self, api_key: str, voice: str = "Cherry",
                 region: str = "beijing", verbose: bool = False):
        """
        初始化实时 TTS 客户端

        Args:
            api_key: DashScope API Key
            voice: 语音名称
            region: 地域 (beijing 或 singapore)
            verbose: 是否显示详细日志
        """
        self.api_key = api_key
        self.voice = voice
        self.region = region
        self.verbose = verbose

        # 设置 API Key
        dashscope.api_key = api_key

        # WebSocket URL
        if region == "singapore":
            self.url = "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"
        else:
            self.url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"

        self.client = None
        self.audio_queue = None

    def start_session(self, mode: str = "server_commit",
                     audio_format: str = "pcm",
                     sample_rate: int = 24000) -> queue.Queue:
        """
        启动实时 TTS 会话

        Args:
            mode: 模式 (server_commit 或 commit)
            audio_format: 音频格式
            sample_rate: 采样率

        Returns:
            音频数据队列
        """
        # 创建音频队列
        self.audio_queue = queue.Queue()

        # 创建回调
        callback = RealtimeTTSCallback(self.audio_queue, verbose=self.verbose)

        # 创建客户端
        self.client = QwenTtsRealtime(
            model='qwen3-tts-flash-realtime',
            callback=callback,
            url=self.url
        )

        # 连接
        self.client.connect()

        # 配置会话
        if audio_format == "pcm":
            if sample_rate == 24000:
                format_enum = AudioFormat.PCM_24000HZ_MONO_16BIT
            elif sample_rate == 48000:
                format_enum = AudioFormat.PCM_48000HZ_MONO_16BIT
            else:
                format_enum = AudioFormat.PCM_24000HZ_MONO_16BIT
        elif audio_format == "mp3":
            format_enum = AudioFormat.MP3_24000HZ_MONO
        elif audio_format == "opus":
            format_enum = AudioFormat.OPUS_24000HZ_MONO
        else:
            format_enum = AudioFormat.PCM_24000HZ_MONO_16BIT

        self.client.update_session(
            voice=self.voice,
            response_format=format_enum,
            mode=mode
        )

        if self.verbose:
            print(f'[实时TTS] 会话已启动: voice={self.voice}, mode={mode}')

        return self.audio_queue

    def send_text(self, text: str):
        """
        发送文本进行合成

        Args:
            text: 要合成的文本
        """
        if self.client:
            self.client.append_text(text)
            if self.verbose:
                print(f'[实时TTS] 发送文本: {text[:50]}...')
        else:
            raise RuntimeError("会话未启动，请先调用 start_session()")

    def finish(self):
        """结束会话"""
        if self.client:
            self.client.finish()
            if self.verbose:
                print('[实时TTS] 会话结束信号已发送')

    def wait_for_completion(self, timeout=None):
        """等待会话完成"""
        if self.client and hasattr(self.client, 'callback'):
            return self.client.callback.wait_for_finished(timeout)
        return False

    def get_metrics(self) -> dict:
        """获取性能指标"""
        if self.client:
            return {
                "session_id": self.client.get_session_id(),
                "first_audio_delay": self.client.get_first_audio_delay(),
                "last_response_id": self.client.get_last_response_id()
            }
        return {}

    def get_available_voices(self) -> list:
        """获取可用的语音列表"""
        return [
            "Cherry",           # 芊悦 - 阳光积极、亲切自然小姐姐
            "Serena",          # 苏瑶 - 温柔小姐姐
            "Ethan",           # 晨煦 - 阳光、温暖、活力的男性
            "Chelsie",         # 千雪 - 二次元虚拟女友
            "Stella",          # 星辰 - 知性优雅女声
            "Lyra",            # 琳雅 - 清新甜美女声
            "Aria",            # 艾瑞 - 专业播音女声
            "Zoe",             # 佐伊 - 活泼可爱女声
            "Nova",            # 诺娃 - 科技感女声
            "Luna",            # 露娜 - 温柔治愈女声
            "Oliver",          # 奥利弗 - 成熟稳重男声
            "Leo",             # 里奥 - 年轻活力男声
            "Mason",           # 梅森 - 磁性低沉男声
            "Ryan",            # 瑞恩 - 专业播音男声
        ]
