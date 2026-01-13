"""
使用 PyAudio 实现真正的流式播放
边接收 PCM 数据边播放，无缓冲延迟
支持 AEC 参考信号回调
"""
import queue
import threading
from typing import Optional, Callable


class PyAudioStreamPlayer:
    """使用 PyAudio 的流式播放器"""

    def __init__(self, sample_rate: int = 24000, channels: int = 1,
                 sample_width: int = 2, reference_callback: Optional[Callable[[bytes], None]] = None):
        """
        初始化播放器

        Args:
            sample_rate: 采样率
            channels: 声道数
            sample_width: 采样宽度（字节）
            reference_callback: 参考音频回调函数（用于 AEC）
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.reference_callback = reference_callback
        self.is_playing = False
        self.audio = None
        self.stream = None

    def play_stream(self, audio_queue: queue.Queue, blocking: bool = True):
        """
        播放音频流

        Args:
            audio_queue: 音频数据队列
            blocking: 是否阻塞
        """
        if blocking:
            self._play_stream_blocking(audio_queue)
        else:
            thread = threading.Thread(
                target=self._play_stream_blocking,
                args=(audio_queue,),
                daemon=True
            )
            thread.start()

    def _play_stream_blocking(self, audio_queue: queue.Queue):
        """阻塞式播放"""
        try:
            import pyaudio

            # 初始化 PyAudio
            self.audio = pyaudio.PyAudio()

            # 打开音频流
            self.stream = self.audio.open(
                format=self.audio.get_format_from_width(self.sample_width),
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=1024  # 小缓冲区，降低延迟
            )

            self.is_playing = True
            # print('[播放器] PyAudio 流式播放已启动')  # 静默

            total_bytes = 0
            chunk_count = 0

            # 从队列读取并播放
            while self.is_playing:
                try:
                    audio_chunk = audio_queue.get(timeout=10)

                    if audio_chunk is None:  # 结束信号
                        # print(f'[播放器] 播放完成: {chunk_count} 块, {total_bytes} 字节')  # 静默
                        break

                    # 检查是否被停止
                    if not self.is_playing:
                        # print('[播放器] 播放被中断')  # 静默
                        break

                    # 直接写入音频流
                    self.stream.write(audio_chunk)
                    total_bytes += len(audio_chunk)
                    chunk_count += 1

                    # 如果有参考音频回调，调用它（用于 AEC）
                    if self.reference_callback:
                        self.reference_callback(audio_chunk)

                    # if chunk_count == 1:
                    #     print('[播放器] 首个音频块已播放')  # 静默
                    # elif chunk_count % 20 == 0:
                    #     print(f'[播放器] 已播放 {chunk_count} 块')  # 静默

                except queue.Empty:
                    # print('[播放器] 等待音频数据超时')  # 静默
                    break
                except Exception as e:
                    # 打断时可能出现 PortAudio 错误，静默处理
                    # print(f'❌ 播放错误: {e}')  # 静默
                    break

        except ImportError:
            print('❌ 错误: 未安装 pyaudio')
            print('  安装方法: pip install pyaudio')
        except Exception as e:
            print(f'❌ 播放器错误: {e}')
        finally:
            # 清理资源
            try:
                if self.stream and self.stream.is_active():
                    self.stream.stop_stream()
                if self.stream:
                    self.stream.close()
            except Exception:
                pass  # 忽略清理时的错误

            if self.audio:
                self.audio.terminate()
            self.is_playing = False

    def stop(self):
        """停止播放"""
        self.is_playing = False
        try:
            if self.stream and self.stream.is_active():
                self.stream.stop_stream()
        except Exception as e:
            pass  # 忽略停止时的错误（打断时可能已关闭）
