"""
音频输入模块 - 从麦克风录音
支持 AEC（回声消除）功能
支持聚合设备（硬件 AEC）
"""
import pyaudio
import threading
import queue
import time
import numpy as np
from typing import Callable, Optional


class AudioInput:
    """麦克风音频输入"""

    def __init__(self,
                 sample_rate: int = 16000,
                 chunk_size: int = 1600,  # 100ms @ 16kHz
                 channels: int = 1,
                 format: int = pyaudio.paInt16,
                 enable_aec: bool = False,
                 aec_processor=None,
                 use_aggregate_device: bool = False,
                 device_index: Optional[int] = None):
        """
        初始化音频输入

        Args:
            sample_rate: 采样率（Hz）
            chunk_size: 每次读取的帧数
            channels: 声道数（1=单声道，2=立体声）
            format: 音频格式
            enable_aec: 是否启用 AEC（回声消除）
            aec_processor: AEC 处理器实例
            use_aggregate_device: 是否使用聚合设备（硬件 AEC）
            device_index: 音频设备索引
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.format = format
        self.enable_aec = enable_aec
        self.aec_processor = aec_processor
        self.use_aggregate_device = use_aggregate_device
        self.device_index = device_index

        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.record_thread = None

        # 如果使用聚合设备，自动检测通道数
        if use_aggregate_device and device_index is not None:
            device_info = self.audio.get_device_info_by_index(device_index)
            self.channels = int(device_info['maxInputChannels'])
            print(f"✅ 聚合设备有 {self.channels} 个输入通道")
            print(f"   - 通道 0: 麦克风")
            if self.channels >= 2:
                print(f"   - 通道 1: BlackHole（参考信号）")
            if self.channels >= 3:
                print(f"   - 通道 2: BlackHole 右声道")
        else:
            self.channels = channels

    def start(self, audio_callback: Optional[Callable[[bytes], None]] = None):
        """
        开始录音

        Args:
            audio_callback: 音频数据回调函数
        """
        if self.is_recording:
            # print('[音频输入] 已经在录音中')  # 静默
            return

        self.audio_callback = audio_callback

        # 打开音频流
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,  # 使用指定的设备
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )

        self.is_recording = True
        self.stream.start_stream()

        if self.use_aggregate_device:
            print(f'✅ 已启用硬件 AEC 模式（聚合设备，{self.channels} 通道）')
        # print(f'[音频输入] 开始录音: {self.sample_rate}Hz, {self.channels}声道')  # 静默

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio 回调函数"""
        # if status:
        #     print(f'[音频输入] 状态: {status}')  # 静默

        # 如果使用聚合设备（硬件 AEC）
        if self.use_aggregate_device and self.channels >= 2 and self.enable_aec and self.aec_processor:
            try:
                # 转换为 numpy 数组
                audio_array = np.frombuffer(in_data, dtype=np.int16)

                # 重塑为 (samples, channels)
                audio_array = audio_array.reshape(-1, self.channels)

                # 通道 0: 麦克风
                mic_channel = audio_array[:, 0]

                # 通道 1: BlackHole（参考信号）
                if self.channels == 2:
                    reference_channel = audio_array[:, 1]
                elif self.channels >= 3:
                    # 3 通道：使用左声道或取平均
                    reference_channel = audio_array[:, 1]

                # 计算原始音量
                mic_rms = np.sqrt(np.mean(mic_channel.astype(np.float32) ** 2))
                ref_rms = np.sqrt(np.mean(reference_channel.astype(np.float32) ** 2))

                # 添加参考信号并处理
                self.aec_processor.add_reference(reference_channel)
                processed = self.aec_processor.process(mic_channel)

                # 计算处理后音量
                processed_rms = np.sqrt(np.mean(processed.astype(np.float32) ** 2))

                # 调试：每 50 次打印一次
                if not hasattr(self, '_aec_counter'):
                    self._aec_counter = 0
                self._aec_counter += 1
                if self._aec_counter % 50 == 0:
                    reduction = mic_rms - processed_rms
                    reduction_percent = (reduction / mic_rms * 100) if mic_rms > 0 else 0
                    print(f"[AEC] 麦克风: {mic_rms:.1f}, 参考: {ref_rms:.1f} → 处理后: {processed_rms:.1f} (消除: {reduction:.1f}, {reduction_percent:.1f}%)")

                # 转换回字节
                processed_data = processed.tobytes()

                # 将处理后的音频数据放入队列
                self.audio_queue.put(processed_data)

                # 调用用户回调
                if self.audio_callback:
                    self.audio_callback(processed_data)

            except Exception as e:
                print(f'[音频输入] AEC 处理错误: {e}')
                import traceback
                traceback.print_exc()
                # 如果 AEC 处理失败，使用原始音频（只取通道 0）
                audio_array = np.frombuffer(in_data, dtype=np.int16)
                audio_array = audio_array.reshape(-1, self.channels)
                mic_channel = audio_array[:, 0]
                processed_data = mic_channel.tobytes()
                self.audio_queue.put(processed_data)
                if self.audio_callback:
                    self.audio_callback(processed_data)

        # 如果启用 AEC 但不是聚合设备（软件 AEC，已弃用）
        elif self.enable_aec and self.aec_processor and not self.use_aggregate_device:
            try:
                # 转换为 numpy 数组
                audio_array = np.frombuffer(in_data, dtype=np.int16)

                # 计算原始音量
                original_rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))

                # 应用 AEC 处理
                processed_array = self.aec_processor.process(audio_array)

                # 计算处理后音量
                processed_rms = np.sqrt(np.mean(processed_array.astype(np.float32) ** 2))

                # 调试：每 50 次打印一次
                if not hasattr(self, '_aec_counter'):
                    self._aec_counter = 0
                self._aec_counter += 1
                if self._aec_counter % 50 == 0:
                    reduction = original_rms - processed_rms
                    reduction_percent = (reduction / original_rms * 100) if original_rms > 0 else 0
                    print(f"[AEC] 麦克风: {original_rms:.1f} → {processed_rms:.1f} (消除: {reduction:.1f}, {reduction_percent:.1f}%)")

                # 转换回字节
                processed_data = processed_array.tobytes()

                # 将处理后的音频数据放入队列
                self.audio_queue.put(processed_data)

                # 调用用户回调
                if self.audio_callback:
                    self.audio_callback(processed_data)
            except Exception as e:
                print(f'[音频输入] AEC 处理错误: {e}')
                # 如果 AEC 处理失败，使用原始音频
                self.audio_queue.put(in_data)
                if self.audio_callback:
                    self.audio_callback(in_data)
        else:
            # 不使用 AEC，直接传递
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

        # print('[音频输入] 停止录音')  # 静默

    def add_reference_audio(self, audio_data: bytes):
        """
        添加参考音频（扬声器输出）到 AEC 处理器

        Args:
            audio_data: 扬声器播放的音频数据（bytes）
        """
        if self.enable_aec and self.aec_processor:
            try:
                # 转换为 numpy 数组
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                # 添加到 AEC 处理器
                self.aec_processor.add_reference(audio_array)
            except Exception as e:
                print(f'[音频输入] 添加参考音频错误: {e}')

    def close(self):
        """关闭音频设备"""
        self.stop()
        if self.audio:
            self.audio.terminate()
            self.audio = None
        # print('[音频输入] 音频设备已关闭')  # 静默

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
