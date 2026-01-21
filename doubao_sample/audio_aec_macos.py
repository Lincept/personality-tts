import logging
import queue
import sys
import threading
from dataclasses import dataclass
from typing import Optional, Any
import time
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PCMFormat:
    sample_rate: int
    channels: int
    sample_format: str  # "f32" | "s16"


class MacOSVPIOAudioIO:
    """macOS VPIO(AEC) 音频 IO。

    关键点：
    - 麦克风：用 AVAudioEngine inputNode + setVoiceProcessingEnabled(True)
    - 播放：远端音频必须通过同一个 AVAudioEngine 的 playerNode 播出，AEC 才能参考回放信号

    说明：这里为了保持实现精简、可控，不引入 AVAudioConverter，使用 numpy 做简单重采样到目标采样率。
    """

    def __init__(
        self,
        input_target: PCMFormat,
        output_source: PCMFormat,
        input_chunk_frames: int,
        queue_max: int = 50,
    ) -> None:
        if sys.platform != "darwin":
            raise RuntimeError("MacOSVPIOAudioIO can only run on macOS")

        try:
            import objc  # noqa: F401
            import AVFoundation
        except Exception as e:
            raise RuntimeError(
                "macOS AEC 需要 pyobjc: pip install pyobjc-framework-AVFoundation pyobjc-framework-Cocoa"
            ) from e

        self.AVFoundation: Any = AVFoundation

        self.input_target = input_target
        self.output_source = output_source
        self.input_chunk_frames = int(input_chunk_frames)

        self.engine = AVFoundation.AVAudioEngine.alloc().init()  # type: ignore[attr-defined]
        self.input_node = self.engine.inputNode()
        self.player_node = AVFoundation.AVAudioPlayerNode.alloc().init()  # type: ignore[attr-defined]
        self.mixer = self.engine.mainMixerNode()

        self._started = False
        self._lock = threading.RLock()

        self._mic_tap_installed = False

        self._mic_q: queue.Queue[bytes] = queue.Queue(maxsize=queue_max)
        self._mic_accum = bytearray()

        self._mic_bytes_per_sample = 4 if input_target.sample_format == "f32" else 2
        self._mic_chunk_bytes = int(self.input_chunk_frames) * int(self.input_target.channels) * self._mic_bytes_per_sample

        self._mic_total_chunks = 0
        self._mic_total_bytes = 0
        self._mic_last_push_ts = 0.0

        self._mic_cb_calls = 0
        self._mic_cb_last_log_ts = 0.0
        self._mic_last_frame_length = 0
        self._mic_last_sample_kind = "none"  # float|int16|none

        # 开启 VPIO / AEC
        ok, err = self.input_node.setVoiceProcessingEnabled_error_(True, None)
        if not ok:
            raise RuntimeError(f"enable VPIO failed: {err}")

        # 输入硬件格式（一般 44.1k/48k, float）
        self._hw_in_format = self.input_node.inputFormatForBus_(0)
        self._hw_in_rate = float(self._hw_in_format.sampleRate())

        # 播放格式（按服务器输出配置创建），引擎会自动转换到设备输出
        self._play_format = self._make_av_audio_format(output_source)

        self.engine.attachNode_(self.player_node)
        self.engine.connect_to_fromBus_toBus_format_(
            self.player_node,
            self.mixer,
            0,
            0,
            self._play_format,
        )

    def _make_av_audio_format(self, fmt: PCMFormat):
        AVFoundation = self.AVFoundation
        if fmt.sample_format == "f32":
            common = AVFoundation.AVAudioPCMFormatFloat32  # type: ignore[attr-defined]
        elif fmt.sample_format == "s16":
            common = AVFoundation.AVAudioPCMFormatInt16  # type: ignore[attr-defined]
        else:
            raise ValueError(f"unsupported sample_format: {fmt.sample_format}")

        return AVFoundation.AVAudioFormat.alloc().initWithCommonFormat_sampleRate_channels_interleaved_(  # type: ignore[attr-defined]
            common,
            float(fmt.sample_rate),
            int(fmt.channels),
            False,
        )

    def start(self, play_only: bool = False) -> None:
        with self._lock:
            # 如果已经以 play_only 启动过（用于先播 TTS），这里仍需允许后续安装 mic tap。
            if self._started:
                if (not play_only) and (not self._mic_tap_installed):
                    self._install_mic_tap()
                return

            if not play_only:
                self._install_mic_tap()

            ok, err = self.engine.startAndReturnError_(None)
            if not ok:
                raise RuntimeError(f"AudioEngine start failed: {err}")
            self._started = True

    def _install_mic_tap(self) -> None:
        # 安装 mic tap（输出 bytes 到队列）
        def in_cb(buffer, when):
            try:
                self._mic_cb_calls += 1
                frame_length = int(buffer.frameLength())
                self._mic_last_frame_length = frame_length
                if frame_length <= 0:
                    return

                channel_data_f = buffer.floatChannelData()
                if channel_data_f is not None:
                    self._mic_last_sample_kind = "float"
                    x = np.zeros((frame_length,), dtype=np.float32)
                    for i in range(frame_length):
                        x[i] = channel_data_f[0][i]
                else:
                    channel_data_i16 = buffer.int16ChannelData()
                    if channel_data_i16 is None:
                        self._mic_last_sample_kind = "none"
                        return
                    self._mic_last_sample_kind = "int16"
                    x = np.zeros((frame_length,), dtype=np.float32)
                    for i in range(frame_length):
                        x[i] = float(channel_data_i16[0][i]) / 32768.0

                # 重采样到目标采样率
                if self._hw_in_rate != float(self.input_target.sample_rate):
                    out_len = int(round(len(x) * (self.input_target.sample_rate / self._hw_in_rate)))
                    if out_len <= 0:
                        return
                    xp = np.linspace(0.0, 1.0, num=len(x), endpoint=False, dtype=np.float32)
                    fp = x
                    xq = np.linspace(0.0, 1.0, num=out_len, endpoint=False, dtype=np.float32)
                    x = np.interp(xq, xp, fp).astype(np.float32)

                # float32 -> 目标格式 bytes
                if self.input_target.sample_format == "s16":
                    y = np.clip(x, -1.0, 1.0)
                    y = (y * 32767.0).astype(np.int16)
                    data = y.tobytes()
                elif self.input_target.sample_format == "f32":
                    data = x.astype(np.float32).tobytes()
                else:
                    return

                # 累积并按固定 chunk_bytes 分包（与原 PyAudio 读取 chunk=3200 的节奏一致）
                self._mic_accum.extend(data)
                while len(self._mic_accum) >= self._mic_chunk_bytes:
                    chunk = bytes(self._mic_accum[: self._mic_chunk_bytes])
                    del self._mic_accum[: self._mic_chunk_bytes]

                    try:
                        self._mic_q.put_nowait(chunk)
                    except queue.Full:
                        # 丢弃最旧的一包，保持实时性
                        try:
                            _ = self._mic_q.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            self._mic_q.put_nowait(chunk)
                        except queue.Full:
                            pass

                    self._mic_total_chunks += 1
                    self._mic_total_bytes += len(chunk)
                    self._mic_last_push_ts = time.time()

                now = time.time()
                if now - self._mic_cb_last_log_ts > 5.0:
                    logger.debug(
                        "mic tap ok: calls=%d frame_len=%d kind=%s pushed_chunks=%d last_push=%.1fs",
                        self._mic_cb_calls,
                        self._mic_last_frame_length,
                        self._mic_last_sample_kind,
                        self._mic_total_chunks,
                        (now - self._mic_last_push_ts) if self._mic_last_push_ts else -1.0,
                    )
                    self._mic_cb_last_log_ts = now

            except Exception as e:
                logger.debug(f"mic tap error: {e}")

        # tap 的 bufferSize 是“硬件帧数”。为了得到目标 chunk(比如 16k@3200)的相近节奏，按采样率比例放大。
        desired_hw_frames = int(round(self.input_chunk_frames * (self._hw_in_rate / float(self.input_target.sample_rate))))
        if desired_hw_frames < 256:
            desired_hw_frames = 256

        self.input_node.installTapOnBus_bufferSize_format_block_(
            0,
            int(desired_hw_frames),
            self._hw_in_format,
            in_cb,
        )
        self._mic_tap_installed = True

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            try:
                if self._mic_tap_installed:
                    self.input_node.removeTapOnBus_(0)
            except Exception:
                pass
            try:
                self.mixer.removeTapOnBus_(0)
            except Exception:
                pass
            try:
                self.engine.stop()
            except Exception:
                pass
            self._started = False
            self._mic_tap_installed = False

    def get_mic_bytes(self, timeout: float = 1.0) -> Optional[bytes]:
        try:
            return self._mic_q.get(timeout=timeout)
        except queue.Empty:
            return None

    def play_bytes(self, audio_bytes: bytes) -> None:
        """播放服务器下发的音频 bytes（必须走本引擎播放，AEC 才有效）。"""
        if not audio_bytes:
            return
        with self._lock:
            if not self._started:
                # 文本模式/仅播放场景：确保能出声
                try:
                    self.start(play_only=True)
                except Exception as e:
                    logger.warning(f"AEC audio engine start failed (play_only): {e}")
                    return

            fmt = self._play_format
            bytes_per_sample = 4 if self.output_source.sample_format == "f32" else 2
            bytes_per_frame = bytes_per_sample * int(self.output_source.channels)
            if bytes_per_frame <= 0:
                return
            frames = int(len(audio_bytes) // bytes_per_frame)
            if frames <= 0:
                return

            buf = self.AVFoundation.AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(fmt, frames)  # type: ignore[attr-defined]
            buf.setFrameLength_(frames)

            if self.output_source.sample_format == "f32":
                arr = np.frombuffer(audio_bytes, dtype=np.float32, count=frames)
                ptr = buf.floatChannelData()
                if ptr is None:
                    return
                for i in range(frames):
                    ptr[0][i] = float(arr[i])
            else:
                arr = np.frombuffer(audio_bytes, dtype=np.int16, count=frames)
                ptr = buf.int16ChannelData()
                if ptr is None:
                    return
                for i in range(frames):
                    ptr[0][i] = int(arr[i])

            self.player_node.scheduleBuffer_completionHandler_(buf, None)
            if not self.player_node.isPlaying():
                self.player_node.play()
