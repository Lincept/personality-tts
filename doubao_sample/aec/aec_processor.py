"""
WebRTC AEC 处理器 - 基于官方 WebRTC 库
用于回声消除，解决语音助手中的回声问题
"""
import platform
from collections import deque
from typing import Optional
import numpy as np
import sys
import os
import threading

# 添加 src 目录到路径
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from . import WebRTCAudioProcessing, create_default_config
    WEBRTC_AVAILABLE = True
except Exception as e:
    print(f"⚠️ WebRTC AEC 库加载失败: {e}")
    WEBRTC_AVAILABLE = False


class WebRTCAECProcessor:
    """
    WebRTC 回声消除处理器
    专门用于处理参考信号（扬声器输出）和麦克风输入的 AEC
    """

    def __init__(self, sample_rate: int = 16000):
        """
        初始化 AEC 处理器

        Args:
            sample_rate: 采样率（默认 16000Hz）
        """
        self.sample_rate = sample_rate
        self._platform = platform.system().lower()
        self._is_macos = self._platform == "darwin"

        # WebRTC APM 实例
        self.apm = None
        self.capture_config = None
        self.render_config = None

        # 参考信号缓冲区
        self._reference_buffer = deque()
        self._webrtc_frame_size = 160  # WebRTC 标准：16kHz, 10ms = 160 samples

        # 状态标志
        self._is_initialized = False

        # 线程锁（保护 WebRTC APM 调用）
        self._lock = threading.Lock()
        
        # 调试和统计
        self._debug = False  # 设置为 True 可以看到详细日志
        self._stats = {
            'frames_processed': 0,
            'reference_frames_added': 0,
            'zero_reference_count': 0,
        }

        # 初始化
        self._initialize()

    def _initialize(self):
        """初始化 WebRTC AEC - 参考 py-xiaozhi 优化配置"""
        if not self._is_macos:
            print(f"⚠️ {self._platform.capitalize()} 平台暂不支持 WebRTC AEC")
            return

        if not WEBRTC_AVAILABLE:
            print("⚠️ WebRTC 库不可用")
            return

        try:
            # 创建 WebRTC APM 实例
            self.apm = WebRTCAudioProcessing()

            # 创建配置 - 参考 py-xiaozhi 的优化配置
            apm_config = create_default_config()

            # Pipeline 配置 - 使用 WebRTC 优化频率
            apm_config.pipeline_config.maximum_internal_processing_rate = 16000  # WebRTC 优化频率
            apm_config.pipeline_config.multi_channel_render = False
            apm_config.pipeline_config.multi_channel_capture = False

            # 启用回声消除 - 使用标准模式
            apm_config.echo.enabled = True
            apm_config.echo.mobile_mode = False  # 标准模式，非移动模式
            apm_config.echo.enforce_high_pass_filtering = True  # 强制高通滤波

            # 启用噪声抑制 - 中等级别（避免过度抑制）
            apm_config.noise_suppress.enabled = True
            apm_config.noise_suppress.noise_level = 1  # MODERATE（中等）
            apm_config.noise_suppress.analyze_linear_aec_output_when_available = True

            # 启用高通滤波器
            apm_config.high_pass.enabled = True
            apm_config.high_pass.apply_in_full_band = True

            # 禁用 PreAmplifier（避免失真）
            apm_config.pre_amp.enabled = False
            apm_config.pre_amp.fixed_gain_factor = 1.0

            # 禁用 LevelAdjustment（减少处理冲突）
            apm_config.level_adjustment.enabled = False

            # 禁用 TransientSuppression（避免切割语音）
            apm_config.transient_suppress.enabled = False

            # 启用 GainController1 - 轻度增益控制
            apm_config.gain_control1.enabled = True
            apm_config.gain_control1.controller_mode = 1  # ADAPTIVE_DIGITAL
            apm_config.gain_control1.target_level_dbfs = 3
            apm_config.gain_control1.compression_gain_db = 9
            apm_config.gain_control1.enable_limiter = True

            # 禁用 GainController2（避免冲突）
            apm_config.gain_control2.enabled = False

            # 应用配置
            result = self.apm.apply_config(apm_config)
            if result != 0:
                raise RuntimeError(f"WebRTC APM 配置失败，错误码: {result}")

            # 创建流配置
            self.capture_config = self.apm.create_stream_config(self.sample_rate, 1)
            self.render_config = self.apm.create_stream_config(self.sample_rate, 1)

            # 设置流延迟 - 关键修复！参考 py-xiaozhi
            self.apm.set_stream_delay_ms(40)  # 40ms 延迟（考虑实际传播和处理延迟）

            self._is_initialized = True
            print("✅ WebRTC AEC 初始化完成（优化配置）")
            print("   - 回声消除: 已启用（标准模式）")
            print("   - 噪声抑制: MODERATE（中等）")
            print("   - 高通滤波: 已启用")
            print("   - 流延迟: 40ms（优化）")
            print("   - 增益控制: 自适应数字")

        except Exception as e:
            print(f"❌ WebRTC AEC 初始化失败: {e}")
            self._is_initialized = False

    def add_reference(self, reference_audio: np.ndarray):
        """
        添加参考信号（扬声器播放的音频）

        Args:
            reference_audio: 参考信号（int16 或 float32）
        """
        if not self._is_initialized:
            return

        # 转换为 int16
        if reference_audio.dtype == np.float32:
            # float32 范围 [-1.0, 1.0] 转换为 int16 范围 [-32768, 32767]
            reference_audio = np.clip(reference_audio * 32768.0, -32768, 32767).astype(np.int16)
        elif reference_audio.dtype != np.int16:
            reference_audio = reference_audio.astype(np.int16)

        # 添加到缓冲区
        self._reference_buffer.extend(reference_audio)
        self._stats['reference_frames_added'] += len(reference_audio) // self._webrtc_frame_size

        # 保持缓冲区大小合理（保留 500ms 用于延迟补偿）
        max_buffer_size = self._webrtc_frame_size * 50  # 500ms @ 16kHz
        while len(self._reference_buffer) > max_buffer_size:
            self._reference_buffer.popleft()
        
        if self._debug and len(self._reference_buffer) > 0:
            print(f"🔊 参考信号: +{len(reference_audio)} samples, 缓冲区: {len(self._reference_buffer)} samples ({len(self._reference_buffer)/160:.1f} 帧)")

    def process(self, capture_audio: np.ndarray) -> np.ndarray:
        """
        处理麦克风音频，应用 AEC

        Args:
            capture_audio: 麦克风采集的音频数据（int16）

        Returns:
            处理后的音频数据（int16）
        """
        if not self._is_initialized or self.apm is None:
            return capture_audio

        # 使用线程锁保护 WebRTC APM 调用
        with self._lock:
            try:
                # 更新统计
                self._stats['frames_processed'] += 1
                
                # 检查输入帧大小是否为 WebRTC 帧大小的整数倍
                if len(capture_audio) % self._webrtc_frame_size != 0:
                    print(f"⚠️ 音频帧大小不是 WebRTC 帧的整数倍: {len(capture_audio)}")
                    return capture_audio

                # 计算需要分割的块数
                num_chunks = len(capture_audio) // self._webrtc_frame_size

                if num_chunks == 1:
                    # 10ms 帧，直接处理
                    result = self._process_single_frame(capture_audio)
                else:
                    # 20ms/40ms/60ms 帧，分割处理
                    result = self._process_chunked_frames(capture_audio, num_chunks)
                
                # 定期输出统计信息
                if self._debug and self._stats['frames_processed'] % 100 == 0:
                    print(f"📊 AEC 统计: 已处理 {self._stats['frames_processed']} 帧, "
                          f"参考帧 {self._stats['reference_frames_added']}, "
                          f"零参考 {self._stats['zero_reference_count']}")
                
                return result

            except Exception as e:
                print(f"⚠️ AEC 处理失败: {e}")
                import traceback
                traceback.print_exc()
                return capture_audio

    def _process_single_frame(self, capture_audio: np.ndarray) -> np.ndarray:
        """处理单个 10ms WebRTC 帧"""
        import ctypes

        try:
            # 确保输入是正确的类型和大小
            if len(capture_audio) != self._webrtc_frame_size:
                print(f"⚠️ 帧大小不匹配: {len(capture_audio)} != {self._webrtc_frame_size}")
                return capture_audio

            # 确保是 int16 类型
            if capture_audio.dtype != np.int16:
                capture_audio = capture_audio.astype(np.int16)

            # 获取参考信号
            reference_audio = self._get_reference_frame(self._webrtc_frame_size)

            # 确保参考信号也是正确的类型和大小
            if len(reference_audio) != self._webrtc_frame_size:
                reference_audio = np.zeros(self._webrtc_frame_size, dtype=np.int16)

            # 创建 ctypes 缓冲区 - 使用 python3.7 项目的方式
            capture_buffer = (ctypes.c_short * self._webrtc_frame_size)(*capture_audio)
            reference_buffer = (ctypes.c_short * self._webrtc_frame_size)(*reference_audio)

            processed_capture = (ctypes.c_short * self._webrtc_frame_size)()
            processed_reference = (ctypes.c_short * self._webrtc_frame_size)()

            # 首先处理参考信号（render stream）
            render_result = self.apm.process_reverse_stream(
                reference_buffer,
                self.render_config,
                self.render_config,
                processed_reference,
            )

            if render_result != 0:
                print(f"⚠️ 参考信号处理失败，错误码: {render_result}")

            # 然后处理采集信号（capture stream）
            capture_result = self.apm.process_stream(
                capture_buffer,
                self.capture_config,
                self.capture_config,
                processed_capture,
            )

            if capture_result != 0:
                print(f"⚠️ 采集信号处理失败，错误码: {capture_result}")
                return capture_audio

            # 转换回 numpy 数组
            return np.array(processed_capture, dtype=np.int16)

        except Exception as e:
            print(f"⚠️ AEC 帧处理失败: {e}")
            import traceback
            traceback.print_exc()
            return capture_audio

    def _process_chunked_frames(self, capture_audio: np.ndarray, num_chunks: int) -> np.ndarray:
        """分割处理大帧（20ms/40ms/60ms 等）"""
        processed_chunks = []

        for i in range(num_chunks):
            # 提取当前 10ms 块
            start_idx = i * self._webrtc_frame_size
            end_idx = (i + 1) * self._webrtc_frame_size
            chunk = capture_audio[start_idx:end_idx]

            # 处理这个 10ms 块
            processed_chunk = self._process_single_frame(chunk)
            processed_chunks.append(processed_chunk)

        # 将所有处理后的块重新组合
        return np.concatenate(processed_chunks)

    def _get_reference_frame(self, frame_size: int) -> np.ndarray:
        """获取指定大小的参考信号帧
        
        策略：从缓冲区头部消耗参考信号，保持与麦克风采集的同步。
        参考信号应该先于麦克风信号送入 AEC（扬声器播放 → 传播 → 麦克风听到）。
        """
        # 如果没有参考信号或缓冲区不足，返回静音
        if len(self._reference_buffer) < frame_size:
            if self._debug:
                print(f"⚠️ 参考信号不足: {len(self._reference_buffer)}/{frame_size}")
            self._stats['zero_reference_count'] += 1
            return np.zeros(frame_size, dtype=np.int16)

        # 从缓冲区头部提取并消耗一帧
        # 这样可以保持参考信号和采集信号的时序关系
        frame_data = []
        for _ in range(frame_size):
            if len(self._reference_buffer) > 0:
                frame_data.append(self._reference_buffer.popleft())
            else:
                frame_data.append(0)

        return np.array(frame_data, dtype=np.int16)

    def enable_debug(self, enable: bool = True):
        """启用或禁用调试模式"""
        self._debug = enable
        if enable:
            print("🐛 AEC 调试模式已启用")
        else:
            print("✅ AEC 调试模式已禁用")
    
    def get_stats(self) -> dict:
        """获取 AEC 统计信息"""
        return self._stats.copy()
    
    def print_stats(self):
        """打印 AEC 统计信息"""
        print("\n" + "="*60)
        print("AEC 统计信息")
        print("="*60)
        print(f"已处理帧数: {self._stats['frames_processed']}")
        print(f"已添加参考帧: {self._stats['reference_frames_added']}")
        print(f"零参考计数: {self._stats['zero_reference_count']}")
        if self._stats['frames_processed'] > 0:
            zero_ratio = self._stats['zero_reference_count'] / self._stats['frames_processed'] * 100
            print(f"零参考比例: {zero_ratio:.1f}%")
            if zero_ratio > 50:
                print("⚠️  警告：超过 50% 的帧没有参考信号！")
                print("   可能原因：扬声器音量太低或没有播放声音")
        print(f"缓冲区当前大小: {len(self._reference_buffer)} samples")
        print("="*60 + "\n")

    def close(self):
        """关闭 AEC 处理器"""
        # 打印最终统计
        if self._stats['frames_processed'] > 0:
            self.print_stats()
        
        if self.apm:
            try:
                if self.capture_config:
                    self.apm.destroy_stream_config(self.capture_config)
                if self.render_config:
                    self.apm.destroy_stream_config(self.render_config)
            except Exception as e:
                print(f"⚠️ 清理 APM 配置失败: {e}")
            finally:
                self.capture_config = None
                self.render_config = None
                self.apm = None

        self._reference_buffer.clear()
        self._is_initialized = False
        print("✅ WebRTC AEC 已关闭")


# 兼容旧代码
class SimpleAEC(WebRTCAECProcessor):
    """兼容旧代码的别名"""
    pass
