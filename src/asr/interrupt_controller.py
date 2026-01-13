"""
打断控制器 - 检测用户说话并停止 TTS 播放
实现类似打电话的交互体验
"""
import threading
import time
from typing import Callable, Optional



class InterruptController:
    """打断控制器"""

    def __init__(self,
                 vad_threshold: float = 0.5,
                 interrupt_delay: float = 0.3):
        """
        初始化打断控制器

        Args:
            vad_threshold: VAD 阈值（0-1），越高越严格
            interrupt_delay: 打断延迟（秒），检测到语音后多久触发打断
        """
        self.vad_threshold = vad_threshold
        self.interrupt_delay = interrupt_delay

        self.is_monitoring = False
        self.is_speaking = False  # TTS 是否正在播放
        self.interrupt_callback = None

        self.last_voice_time = 0
        self.interrupt_triggered = False

    def start_monitoring(self, interrupt_callback: Callable[[], None]):
        """
        开始监听打断

        Args:
            interrupt_callback: 检测到打断时的回调函数
        """
        self.interrupt_callback = interrupt_callback
        self.is_monitoring = True
        self.interrupt_triggered = False

    def stop_monitoring(self):
        """停止监听打断"""
        self.is_monitoring = False

    def set_tts_speaking(self, is_speaking: bool):
        """
        设置 TTS 播放状态

        Args:
            is_speaking: TTS 是否正在播放
        """
        self.is_speaking = is_speaking
        if not is_speaking:
            # TTS 停止时重置打断状态
            self.interrupt_triggered = False

    def on_voice_detected(self, has_voice: bool):
        """
        语音检测回调

        Args:
            has_voice: 是否检测到语音
        """
        if not self.is_monitoring:
            return

        current_time = time.time()

        if has_voice:
            self.last_voice_time = current_time

            # 如果 TTS 正在播放且还未触发打断
            if self.is_speaking and not self.interrupt_triggered:
                # 检查是否超过延迟阈值
                if current_time - self.last_voice_time >= self.interrupt_delay:
                    self._trigger_interrupt()

    def on_asr_text(self, text: str, is_final: bool):
        """
        ASR 文本回调（用于更精确的打断检测）

        Args:
            text: 识别的文本
            is_final: 是否是最终结果
        """
        if not self.is_monitoring:
            return

        # 如果识别到文本且 TTS 正在播放
        if text and self.is_speaking and not self.interrupt_triggered:
            # 立即触发打断
            self._trigger_interrupt()

    def _trigger_interrupt(self):
        """触发打断"""
        if self.interrupt_triggered:
            return

        self.interrupt_triggered = True

        if self.interrupt_callback:
            self.interrupt_callback()

    def reset(self):
        """重置状态"""
        self.interrupt_triggered = False
        self.last_voice_time = 0
        self.is_speaking = False
