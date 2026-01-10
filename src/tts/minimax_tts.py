"""
MiniMax TTS API 封装
"""
import json
import requests
from typing import Optional


class MiniMaxTTS:
    def __init__(self, api_key: str, group_id: str,
                 voice: str = "female-tianmei"):
        """
        初始化 MiniMax TTS 客户端

        Args:
            api_key: MiniMax API Key
            group_id: MiniMax Group ID
            voice: 语音模型名称
        """
        self.api_key = api_key
        self.group_id = group_id
        self.voice = voice
        self.base_url = "https://api.minimax.chat/v1/text_to_speech"

    def synthesize(self, text: str, output_path: str,
                   format: str = "mp3", sample_rate: int = 24000) -> dict:
        """
        将文本转换为语音

        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            format: 音频格式 (mp3, wav, pcm)
            sample_rate: 采样率

        Returns:
            包含状态和信息的字典
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "group_id": self.group_id,
                "text": text,
                "voice_id": self.voice,
                "model": "speech-01",
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
                "audio_sample_rate": sample_rate,
                "bitrate": 128000,
                "format": format
            }

            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("base_resp", {}).get("status_code") == 0:
                    # 获取音频URL或数据
                    audio_url = result.get("audio_file", "")

                    if audio_url:
                        # 下载音频文件
                        audio_response = requests.get(audio_url, timeout=30)
                        if audio_response.status_code == 200:
                            with open(output_path, 'wb') as f:
                                f.write(audio_response.content)

                            return {
                                "success": True,
                                "output_path": output_path,
                                "provider": "minimax",
                                "voice": self.voice,
                                "text_length": len(text),
                                "audio_url": audio_url
                            }
                    else:
                        # 直接返回音频数据
                        audio_data = result.get("data", {}).get("audio", "")
                        if audio_data:
                            import base64
                            audio_bytes = base64.b64decode(audio_data)
                            with open(output_path, 'wb') as f:
                                f.write(audio_bytes)

                            return {
                                "success": True,
                                "output_path": output_path,
                                "provider": "minimax",
                                "voice": self.voice,
                                "text_length": len(text)
                            }

                    return {
                        "success": False,
                        "error": "No audio data returned",
                        "provider": "minimax"
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("base_resp", {}).get("status_msg", "Unknown error"),
                        "provider": "minimax"
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "provider": "minimax"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "minimax"
            }

    def synthesize_stream(self, text: str, output_path: str) -> dict:
        """
        流式合成语音

        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径

        Returns:
            包含状态和信息的字典
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "group_id": self.group_id,
                "text": text,
                "voice_id": self.voice,
                "model": "speech-01-turbo",  # 使用turbo模型支持流式
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
                "stream": True
            }

            response = requests.post(
                f"{self.base_url}?stream=true",
                headers=headers,
                json=payload,
                stream=True,
                timeout=30
            )

            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                return {
                    "success": True,
                    "output_path": output_path,
                    "provider": "minimax",
                    "voice": self.voice,
                    "mode": "streaming"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "provider": "minimax"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "minimax"
            }

    def get_available_voices(self) -> list:
        """
        获取可用的语音列表

        Returns:
            语音列表
        """
        return [
            "female-tianmei",         # 甜美女声
            "female-wenrou",          # 温柔女声
            "male-qingse",            # 青涩男声
            "male-chenwen",           # 沉稳男声
            "presenter_male",         # 男性主播
            "presenter_female",       # 女性主播
            "audiobook_male_1",       # 男性有声书1
            "audiobook_female_1",     # 女性有声书1
        ]
