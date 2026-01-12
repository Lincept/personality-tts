"""
火山引擎 Seed2 TTS API 封装
"""
import json
import requests
import base64
from typing import Optional


class VolcengineSeed2TTS:
    def __init__(self, app_id: str, access_token: str = None, api_key: str = None,
                 voice: str = "zh_female_qingxin"):
        """
        初始化火山引擎 Seed2 TTS 客户端

        Args:
            app_id: 火山引擎应用ID
            access_token: 访问令牌（旧版，兼容）
            api_key: API Key（新版，推荐）
            voice: 语音模型名称
        """
        self.app_id = app_id
        # 优先使用 api_key，如果没有则使用 access_token
        self.token = api_key if api_key else access_token
        self.voice = voice
        self.base_url = "https://openspeech.bytedance.com/api/v1/tts"

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
                "Authorization": f"Bearer; {self.token}",
                "Content-Type": "application/json"
            }

            payload = {
                "app": {
                    "appid": self.app_id,
                    "token": self.token,
                    "cluster": "volcano_tts"
                },
                "user": {
                    "uid": "user_001"
                },
                "audio": {
                    "voice_type": self.voice,
                    "encoding": format,
                    "speed_ratio": 1.0,
                    "volume_ratio": 1.0,
                    "pitch_ratio": 1.0,
                    "sample_rate": sample_rate
                },
                "request": {
                    "reqid": "test_request_001",
                    "text": text,
                    "text_type": "plain",
                    "operation": "submit"
                }
            }

            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("code") == 0:
                    # 获取音频数据
                    audio_data = result.get("data", {})

                    # 如果返回的是base64编码的音频
                    if "audio" in audio_data:
                        audio_bytes = base64.b64decode(audio_data["audio"])
                    else:
                        audio_bytes = response.content

                    # 保存音频文件
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)

                    return {
                        "success": True,
                        "output_path": output_path,
                        "provider": "volcengine_seed2",
                        "voice": self.voice,
                        "text_length": len(text)
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("message", "Unknown error"),
                        "provider": "volcengine_seed2"
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "provider": "volcengine_seed2"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "volcengine_seed2"
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
                "Authorization": f"Bearer; {self.token}",
                "Content-Type": "application/json"
            }

            payload = {
                "app": {
                    "appid": self.app_id,
                    "token": self.token,
                    "cluster": "volcano_tts"
                },
                "user": {
                    "uid": "user_001"
                },
                "audio": {
                    "voice_type": self.voice,
                    "encoding": "mp3",
                    "speed_ratio": 1.0,
                    "volume_ratio": 1.0,
                    "pitch_ratio": 1.0
                },
                "request": {
                    "reqid": "test_stream_001",
                    "text": text,
                    "text_type": "plain",
                    "operation": "query",
                    "with_frontend": 1,
                    "frontend_type": "unitTson"
                }
            }

            response = requests.post(
                self.base_url,
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
                    "provider": "volcengine_seed2",
                    "voice": self.voice,
                    "mode": "streaming"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "provider": "volcengine_seed2"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "volcengine_seed2"
            }

    def get_available_voices(self) -> list:
        """
        获取可用的语音列表

        Returns:
            语音列表
        """
        return [
            "zh_female_qingxin",      # 清新女声
            "zh_male_chunhou",        # 醇厚男声
            "zh_female_wanxin",       # 婉心女声
            "zh_male_qingrun",        # 清润男声
            "zh_female_tianmei",      # 甜美女声
            "zh_male_ziran",          # 自然男声
            "BV700_V2_streaming",     # Seed2 流式语音
        ]
