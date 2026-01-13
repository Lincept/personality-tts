"""
DashScope 实时语音识别客户端
使用 DashScope SDK 的 Recognition 类进行流式识别
"""
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
from typing import Callable, Optional
import time


class RealtimeASRCallback(RecognitionCallback):
    """实时 ASR 回调处理器"""

    def __init__(self,
                 on_text: Optional[Callable[[str], None]] = None,
                 on_sentence: Optional[Callable[[str], None]] = None):
        """
        Args:
            on_text: 接收到中间文本时的回调
            on_sentence: 接收到完整句子时的回调
        """
        self.on_text_callback = on_text
        self.on_sentence_callback = on_sentence
        self.first_result_time = None

    def on_open(self):
        """连接建立"""
        # print('[ASR] 连接已建立')  # 静默
        self.first_result_time = time.time()

    def on_close(self):
        """连接关闭"""
        # print('[ASR] 连接已关闭')  # 静默

    def on_event(self, result: RecognitionResult):
        """处理识别结果"""
        try:
            # 获取识别文本
            if hasattr(result, 'get_sentence'):
                sentence = result.get_sentence()
                if sentence and 'text' in sentence:
                    text = sentence['text']
                    end_time = sentence.get('end_time')
                    is_final = end_time is not None and end_time > 0

                    if is_final:
                        # 完整句子
                        # print(f'\n[ASR] 句子: {text}')  # 静默
                        if self.on_sentence_callback:
                            self.on_sentence_callback(text)
                    else:
                        # 中间结果
                        # print(f'\r[ASR] 中间: {text}', end='', flush=True)  # 静默
                        if self.on_text_callback:
                            self.on_text_callback(text)

                    # 记录首个结果延迟
                    if self.first_result_time:
                        delay = time.time() - self.first_result_time
                        # print(f'\n[ASR] 首个结果延迟: {delay:.3f}秒')  # 静默
                        self.first_result_time = None

        except Exception as e:
            print(f'❌ ASR 结果处理错误: {e}')  # 保留错误信息

    def on_error(self, result: RecognitionResult):
        """处理错误"""
        print(f'❌ ASR 错误: {result}')  # 保留错误信息

    def on_complete(self):
        """识别完成"""
        # print('\n[ASR] 识别完成')  # 静默


class DashScopeASR:
    """DashScope 实时语音识别客户端"""

    def __init__(self, api_key: str, model: str = "fun-asr-realtime-2025-11-07"):
        """
        初始化 ASR 客户端

        Args:
            api_key: DashScope API Key
            model: 模型名称（默认使用 FunASR 2025-11-07 版本）
        """
        self.api_key = api_key
        self.model = model
        self.recognition = None
        self.callback = None
        self.is_running = False

        # 设置 API Key
        dashscope.api_key = api_key

    def start(self,
             on_text: Optional[Callable[[str], None]] = None,
             on_sentence: Optional[Callable[[str], None]] = None,
             sample_rate: int = 16000,
             format: str = "pcm",
             disfluency_removal_enabled: bool = True,
             timestamp_alignment_enabled: bool = False,
             audio_event_detection_enabled: bool = False):
        """
        启动实时识别

        Args:
            on_text: 接收到中间文本时的回调
            on_sentence: 接收到完整句子时的回调
            sample_rate: 采样率（Hz）
            format: 音频格式
            disfluency_removal_enabled: 是否过滤语气词（"嗯"、"啊"等）
            timestamp_alignment_enabled: 是否返回时间戳
            audio_event_detection_enabled: 是否检测音频事件（笑声、咳嗽等）
        """
        # 创建回调
        self.callback = RealtimeASRCallback(
            on_text=on_text,
            on_sentence=on_sentence
        )

        # 创建 Recognition 实例（添加高级参数）
        self.recognition = Recognition(
            model=self.model,
            callback=self.callback,
            format=format,
            sample_rate=sample_rate,
            disfluency_removal_enabled=disfluency_removal_enabled,
            timestamp_alignment_enabled=timestamp_alignment_enabled,
            audio_event_detection_enabled=audio_event_detection_enabled
        )

        # 启动识别
        self.recognition.start()
        self.is_running = True
        # print(f'[ASR] 已启动: model={self.model}, sample_rate={sample_rate}Hz')  # 静默
        # if disfluency_removal_enabled:
        #     print('[ASR] 已启用语气词过滤')  # 静默

    def send_audio(self, audio_data: bytes):
        """
        发送音频数据

        Args:
            audio_data: PCM 音频数据
        """
        if not self.is_running or not self.recognition:
            return

        try:
            self.recognition.send_audio_frame(audio_data)
        except Exception as e:
            print(f'❌ ASR 发送音频失败: {e}')  # 保留错误信息

    def stop(self):
        """停止识别"""
        if not self.is_running or not self.recognition:
            return

        try:
            self.recognition.stop()
            self.is_running = False
            # print('\n[ASR] 已停止')  # 静默
        except Exception as e:
            print(f'❌ ASR 停止失败: {e}')  # 保留错误信息
