"""
使用 PyAudio 实现真正的流式播放
边接收 PCM 数据边播放，无缓冲延迟
"""
import queue
import threading


class PyAudioStreamPlayer:
    """使用 PyAudio 的流式播放器"""

    def __init__(self, sample_rate: int = 24000, channels: int = 1,
                 sample_width: int = 2):
        """
        初始化播放器

        Args:
            sample_rate: 采样率
            channels: 声道数
            sample_width: 采样宽度（字节）
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
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
            print('[播放器] PyAudio 流式播放已启动')

            total_bytes = 0
            chunk_count = 0

            # 从队列读取并播放
            while True:
                try:
                    audio_chunk = audio_queue.get(timeout=10)

                    if audio_chunk is None:  # 结束信号
                        print(f'[播放器] 播放完成: {chunk_count} 块, {total_bytes} 字节')
                        break

                    # 直接写入音频流
                    self.stream.write(audio_chunk)
                    total_bytes += len(audio_chunk)
                    chunk_count += 1

                    if chunk_count == 1:
                        print('[播放器] 首个音频块已播放')
                    elif chunk_count % 20 == 0:
                        print(f'[播放器] 已播放 {chunk_count} 块')

                except queue.Empty:
                    print('[播放器] 等待音频数据超时')
                    break
                except Exception as e:
                    print(f'[播放器] 播放错误: {e}')
                    break

        except ImportError:
            print('[播放器] 错误: 未安装 pyaudio')
            print('  安装方法: pip install pyaudio')
        except Exception as e:
            print(f'[播放器] 错误: {e}')
            import traceback
            traceback.print_exc()
        finally:
            # 清理资源
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                self.audio.terminate()
            self.is_playing = False

    def stop(self):
        """停止播放"""
        if self.stream:
            self.stream.stop_stream()
        self.is_playing = False
