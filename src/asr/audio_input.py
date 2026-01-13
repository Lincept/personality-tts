"""
音频输入模块 - 从麦克风录音
"""
import pyaudio
import threading
import queue
import time
from typing import Callable, Optional


class AudioInput:
    """麦克风音频输入"""

    def __init__(self,
                 sample_rate: int = 16000,
                 chunk_size: int = 1600,  # 100ms @ 16kHz
                 channels: int = 1,
                 format: int = pyaudio.paInt16):
        """
        初始化音频输入

        Args:
            sample_rate: 采样率（Hz）
            chunk_size: 每次读取的帧数
            channels: 声道数（1=单声道，2=立体声）
            format: 音频格式
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = format

        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.record_thread = None

    def start(self, audio_callback: Optional[Callable[[bytes], None]] = None):
        """
        开始录音

        Args:
            audio_callback: 音频数据回调函数
        """
        if self.is_recording:
            print('[音频输入] 已经在录音中')
            return

        self.audio_callback = audio_callback

        # 打开音频流
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )

        self.is_recording = True
        self.stream.start_stream()
        print(f'[音频输入] 开始录音: {self.sample_rate}Hz, {self.channels}声道')

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio 回调函数"""
        if status:
            print(f'[音频输入] 状态: {status}')

        # 将音频数据放入队列
        self.audio_queue.put(in_data)

        # 调用用户回调
        if self.audio_callback:
            self.audio_callback(in_data)

        return (None, pyaudio.paContinue)

    def stop(self):
        """停止录音"""
        if not self.is_recording:
            return

        self.is_recording = False

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        print('[音频输入] 停止录音')

    def close(self):
        """关闭音频设备"""
        self.stop()
        if self.audio:
            self.audio.terminate()
            self.audio = None
        print('[音频输入] 音频设备已关闭')

    def get_audio_data(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        从队列获取音频数据

        Args:
            timeout: 超时时间（秒）

        Returns:
            音频数据，如果超时返回 None
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def list_devices(self):
        """列出所有音频设备"""
        print('\n可用的音频输入设备:')
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  [{i}] {device_info.get('name')}")
                print(f"      采样率: {int(device_info.get('defaultSampleRate'))}Hz")
                print(f"      输入声道: {device_info.get('maxInputChannels')}")
