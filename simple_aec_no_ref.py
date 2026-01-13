#!/usr/bin/env python3
"""
简化版 AEC 处理器 - 只处理麦克风，不处理参考信号
用于调试 bus error 问题
"""
import numpy as np
import sys
import os
import threading

# 添加 src 目录到路径
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

try:
    from webrtc_apm import WebRTCAudioProcessing, create_default_config
    WEBRTC_AVAILABLE = True
except Exception as e:
    print(f"⚠️ WebRTC AEC 库加载失败: {e}")
    WEBRTC_AVAILABLE = False


class SimpleAECNoReference:
    """简化版 AEC - 不使用参考信号"""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._webrtc_frame_size = 160
        self._is_initialized = False
        self._lock = threading.Lock()

        if not WEBRTC_AVAILABLE:
            print("⚠️ WebRTC 库不可用")
            return

        try:
            # 创建 WebRTC APM 实例
            self.apm = WebRTCAudioProcessing()

            # 创建配置
            apm_config = create_default_config()

            # 只启用噪声抑制和高通滤波，不启用回声消除
            apm_config.echo.enabled = False  # 禁用回声消除
            apm_config.noise_suppress.enabled = True
            apm_config.noise_suppress.noise_level = 2  # HIGH
            apm_config.high_pass.enabled = True
            apm_config.high_pass.apply_in_full_band = True

            # 应用配置
            result = self.apm.apply_config(apm_config)
            if result != 0:
                raise RuntimeError(f"配置失败，错误码: {result}")

            # 创建流配置
            self.capture_config = self.apm.create_stream_config(self.sample_rate, 1)

            self._is_initialized = True
            print("✅ 简化版 AEC 初始化完成（仅噪声抑制）")

        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            self._is_initialized = False

    def add_reference(self, reference_audio: np.ndarray):
        """空实现 - 不处理参考信号"""
        pass

    def process(self, capture_audio: np.ndarray) -> np.ndarray:
        """只处理麦克风音频"""
        if not self._is_initialized or self.apm is None:
            return capture_audio

        with self._lock:
            try:
                # 确保是 int16 类型
                if capture_audio.dtype != np.int16:
                    capture_audio = capture_audio.astype(np.int16)

                # 检查帧大小
                if len(capture_audio) % self._webrtc_frame_size != 0:
                    return capture_audio

                # 分割处理
                num_chunks = len(capture_audio) // self._webrtc_frame_size
                processed_chunks = []

                for i in range(num_chunks):
                    start_idx = i * self._webrtc_frame_size
                    end_idx = (i + 1) * self._webrtc_frame_size
                    chunk = capture_audio[start_idx:end_idx]

                    # 处理单帧
                    processed_chunk = self._process_frame(chunk)
                    processed_chunks.append(processed_chunk)

                return np.concatenate(processed_chunks)

            except Exception as e:
                print(f"⚠️ 处理失败: {e}")
                return capture_audio

    def _process_frame(self, audio: np.ndarray) -> np.ndarray:
        """处理单帧"""
        import ctypes

        try:
            # 使用 numpy 的 ctypes 接口
            input_buffer = audio.ctypes.data_as(ctypes.POINTER(ctypes.c_short))
            output = np.zeros(self._webrtc_frame_size, dtype=np.int16)
            output_buffer = output.ctypes.data_as(ctypes.POINTER(ctypes.c_short))

            # 只处理采集流
            result = self.apm.process_stream(
                input_buffer,
                self.capture_config,
                self.capture_config,
                output_buffer,
            )

            if result != 0:
                return audio

            return output

        except Exception as e:
            print(f"⚠️ 帧处理失败: {e}")
            return audio

    def close(self):
        """关闭处理器"""
        if self.apm:
            try:
                if self.capture_config:
                    self.apm.destroy_stream_config(self.capture_config)
            except Exception as e:
                print(f"⚠️ 清理失败: {e}")
            finally:
                self.capture_config = None
                self.apm = None

        self._is_initialized = False
        print("✅ 简化版 AEC 已关闭")


if __name__ == '__main__':
    # 测试
    print("测试简化版 AEC...")
    aec = SimpleAECNoReference(16000)

    # 生成测试信号
    test_audio = np.random.randint(-1000, 1000, 1600, dtype=np.int16)
    print(f"输入: {len(test_audio)} 样本")

    # 处理
    processed = aec.process(test_audio)
    print(f"输出: {len(processed)} 样本")

    # 关闭
    aec.close()
    print("✅ 测试完成")
