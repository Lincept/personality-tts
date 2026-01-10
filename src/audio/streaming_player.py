"""
流式音频播放器 - 边接收 PCM 数据边播放
支持实时播放，无需等待完整音频文件
"""
import queue
import threading
import subprocess
import platform
import tempfile
import os


class StreamingAudioPlayer:
    """流式音频播放器"""

    def __init__(self, sample_rate: int = 24000, channels: int = 1,
                 sample_width: int = 2):
        """
        初始化流式播放器

        Args:
            sample_rate: 采样率
            channels: 声道数 (1=单声道, 2=立体声)
            sample_width: 采样宽度 (字节数，2=16bit)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.system = platform.system()
        self.process = None
        self.is_playing = False

    def play_stream(self, audio_queue: queue.Queue, blocking: bool = True):
        """
        播放音频流

        Args:
            audio_queue: 音频数据队列
            blocking: 是否阻塞等待播放完成
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
        """阻塞式播放音频流"""
        try:
            if self.system == "Darwin":  # macOS
                self._play_stream_macos(audio_queue)
            elif self.system == "Linux":
                self._play_stream_linux(audio_queue)
            elif self.system == "Windows":
                self._play_stream_windows(audio_queue)
            else:
                print(f"[播放器] 不支持的平台: {self.system}")

        except Exception as e:
            print(f"[播放器] 错误: {e}")
        finally:
            self.is_playing = False

    def _play_stream_macos(self, audio_queue: queue.Queue):
        """macOS 流式播放"""
        # 使用 ffplay 播放 PCM 流
        cmd = [
            'ffplay',
            '-f', 's16le',  # PCM 16-bit little-endian
            '-ar', str(self.sample_rate),  # 采样率
            '-ac', str(self.channels),  # 声道数
            '-nodisp',  # 不显示窗口
            '-autoexit',  # 播放完自动退出
            '-i', '-'  # 从 stdin 读取
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.is_playing = True
            print('[播放器] 开始流式播放 (ffplay)')

            total_bytes = 0
            chunk_count = 0

            # 从队列读取音频数据并写入 ffplay
            while True:
                try:
                    audio_chunk = audio_queue.get(timeout=10)

                    if audio_chunk is None:  # 结束信号
                        print(f'[播放器] 接收到结束信号，共播放 {chunk_count} 个音频块，{total_bytes} 字节')
                        break

                    if self.process and self.process.stdin:
                        try:
                            self.process.stdin.write(audio_chunk)
                            self.process.stdin.flush()
                            total_bytes += len(audio_chunk)
                            chunk_count += 1

                            if chunk_count % 10 == 0:
                                print(f'[播放器] 已播放 {chunk_count} 个音频块')

                        except BrokenPipeError:
                            print('[播放器] 管道断开，尝试重启播放器')
                            # 不要退出，继续接收数据
                            break
                        except Exception as e:
                            print(f'[播放器] 写入错误: {e}')
                            break

                except queue.Empty:
                    print('[播放器] 等待音频数据超时')
                    break

            # 关闭输入流
            if self.process and self.process.stdin:
                try:
                    self.process.stdin.close()
                except:
                    pass

            # 等待播放完成
            if self.process:
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.terminate()

            print('[播放器] 播放完成')

        except FileNotFoundError:
            print('[播放器] 错误: 未找到 ffplay，请安装 ffmpeg')
            print('  安装方法: brew install ffmpeg')
        except Exception as e:
            print(f'[播放器] 错误: {e}')
            import traceback
            traceback.print_exc()

    def _play_stream_linux(self, audio_queue: queue.Queue):
        """Linux 流式播放"""
        # 尝试使用 aplay 或 ffplay
        players = [
            ['aplay', '-f', 'S16_LE', '-r', str(self.sample_rate), '-c', str(self.channels)],
            ['ffplay', '-f', 's16le', '-ar', str(self.sample_rate), '-ac', str(self.channels),
             '-nodisp', '-autoexit', '-']
        ]

        for cmd in players:
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                self.is_playing = True
                print(f'[播放器] 开始流式播放 ({cmd[0]})')

                # 从队列读取并播放
                while True:
                    try:
                        audio_chunk = audio_queue.get(timeout=5)
                        if audio_chunk is None:
                            break
                        if self.process and self.process.stdin:
                            self.process.stdin.write(audio_chunk)
                            self.process.stdin.flush()
                    except queue.Empty:
                        break
                    except BrokenPipeError:
                        break

                if self.process and self.process.stdin:
                    self.process.stdin.close()
                if self.process:
                    self.process.wait()

                print('[播放器] 播放完成')
                return

            except FileNotFoundError:
                continue
            except Exception as e:
                print(f'[播放器] {cmd[0]} 错误: {e}')
                continue

        print('[播放器] 错误: 未找到可用的播放器 (aplay/ffplay)')

    def _play_stream_windows(self, audio_queue: queue.Queue):
        """Windows 流式播放"""
        # 使用 ffplay
        cmd = [
            'ffplay',
            '-f', 's16le',
            '-ar', str(self.sample_rate),
            '-ac', str(self.channels),
            '-nodisp',
            '-autoexit',
            '-'
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.is_playing = True
            print('[播放器] 开始流式播放 (ffplay)')

            while True:
                try:
                    audio_chunk = audio_queue.get(timeout=5)
                    if audio_chunk is None:
                        break
                    if self.process and self.process.stdin:
                        self.process.stdin.write(audio_chunk)
                        self.process.stdin.flush()
                except queue.Empty:
                    break
                except BrokenPipeError:
                    break

            if self.process and self.process.stdin:
                self.process.stdin.close()
            if self.process:
                self.process.wait()

            print('[播放器] 播放完成')

        except FileNotFoundError:
            print('[播放器] 错误: 未找到 ffplay，请安装 ffmpeg')
        except Exception as e:
            print(f'[播放器] 错误: {e}')

    def stop(self):
        """停止播放"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
                print('[播放器] 已停止')
            except Exception as e:
                print(f'[播放器] 停止失败: {e}')
        self.is_playing = False

    def is_active(self) -> bool:
        """检查是否正在播放"""
        return self.is_playing and (self.process is not None) and (self.process.poll() is None)
