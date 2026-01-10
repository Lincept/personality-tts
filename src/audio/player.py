"""
音频播放功能封装
支持多种音频格式的播放
"""
import os
import platform
import subprocess
from typing import Optional
import threading


class AudioPlayer:
    def __init__(self):
        """
        初始化音频播放器
        """
        self.system = platform.system()
        self.current_process = None

    def play(self, audio_path: str, blocking: bool = False) -> dict:
        """
        播放音频文件

        Args:
            audio_path: 音频文件路径
            blocking: 是否阻塞等待播放完成

        Returns:
            包含状态的字典
        """
        if not os.path.exists(audio_path):
            return {
                "success": False,
                "error": f"Audio file not found: {audio_path}"
            }

        try:
            if self.system == "Darwin":  # macOS
                return self._play_macos(audio_path, blocking)
            elif self.system == "Linux":
                return self._play_linux(audio_path, blocking)
            elif self.system == "Windows":
                return self._play_windows(audio_path, blocking)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported platform: {self.system}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _play_macos(self, audio_path: str, blocking: bool) -> dict:
        """
        在 macOS 上播放音频

        Args:
            audio_path: 音频文件路径
            blocking: 是否阻塞

        Returns:
            状态字典
        """
        try:
            if blocking:
                subprocess.run(["afplay", audio_path], check=True)
            else:
                self.current_process = subprocess.Popen(["afplay", audio_path])

            return {
                "success": True,
                "player": "afplay",
                "blocking": blocking
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _play_linux(self, audio_path: str, blocking: bool) -> dict:
        """
        在 Linux 上播放音频

        Args:
            audio_path: 音频文件路径
            blocking: 是否阻塞

        Returns:
            状态字典
        """
        # 尝试多个播放器
        players = ["ffplay", "mpg123", "aplay", "paplay"]

        for player in players:
            try:
                if player == "ffplay":
                    cmd = [player, "-nodisp", "-autoexit", audio_path]
                else:
                    cmd = [player, audio_path]

                if blocking:
                    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
                else:
                    self.current_process = subprocess.Popen(
                        cmd, stderr=subprocess.DEVNULL
                    )

                return {
                    "success": True,
                    "player": player,
                    "blocking": blocking
                }
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        return {
            "success": False,
            "error": "No suitable audio player found. Install ffplay, mpg123, or aplay."
        }

    def _play_windows(self, audio_path: str, blocking: bool) -> dict:
        """
        在 Windows 上播放音频

        Args:
            audio_path: 音频文件路径
            blocking: 是否阻塞

        Returns:
            状态字典
        """
        try:
            import winsound
            if blocking:
                winsound.PlaySound(audio_path, winsound.SND_FILENAME)
            else:
                winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)

            return {
                "success": True,
                "player": "winsound",
                "blocking": blocking
            }
        except Exception as e:
            # 尝试使用 ffplay
            try:
                if blocking:
                    subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_path], check=True)
                else:
                    self.current_process = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", audio_path]
                    )

                return {
                    "success": True,
                    "player": "ffplay",
                    "blocking": blocking
                }
            except Exception as e2:
                return {
                    "success": False,
                    "error": f"Failed to play audio: {str(e)}, {str(e2)}"
                }

    def play_async(self, audio_path: str, callback=None) -> dict:
        """
        异步播放音频

        Args:
            audio_path: 音频文件路径
            callback: 播放完成后的回调函数

        Returns:
            状态字典
        """
        def play_thread():
            result = self.play(audio_path, blocking=True)
            if callback:
                callback(result)

        thread = threading.Thread(target=play_thread, daemon=True)
        thread.start()

        return {
            "success": True,
            "mode": "async",
            "thread_id": thread.ident
        }

    def stop(self) -> dict:
        """
        停止当前播放

        Returns:
            状态字典
        """
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=2)
                return {
                    "success": True,
                    "message": "Playback stopped"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        else:
            return {
                "success": False,
                "error": "No active playback"
            }

    def is_playing(self) -> bool:
        """
        检查是否正在播放

        Returns:
            是否正在播放
        """
        if self.current_process:
            return self.current_process.poll() is None
        return False
