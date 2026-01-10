"""
Qwen3 TTS API 封装
通义千问3 TTS服务 - 使用 qwen3-tts-flash 模型
"""
import json
import os
import base64
from typing import Optional
import dashscope
from dashscope import MultiModalConversation


class Qwen3TTS:
    def __init__(self, api_key: str, voice: str = "Cherry"):
        """
        初始化 Qwen3 TTS 客户端

        Args:
            api_key: 阿里云 DashScope API Key
            voice: 语音模型名称
        """
        self.api_key = api_key
        self.voice = voice
        dashscope.api_key = api_key

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
            import requests

            # 调用 Qwen3 TTS API
            response = MultiModalConversation.call(
                model='qwen3-tts-flash',
                text=text,
                voice=self.voice,
                language_type='Auto',  # 自动检测语言
                stream=False
            )

            if response.status_code == 200:
                # 获取音频对象
                audio = response.output.audio

                # 检查是否有 URL
                if audio.url:
                    # 从 URL 下载音频
                    audio_response = requests.get(audio.url, timeout=30)
                    if audio_response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            f.write(audio_response.content)

                        return {
                            "success": True,
                            "output_path": output_path,
                            "provider": "qwen3",
                            "voice": self.voice,
                            "text_length": len(text),
                            "audio_url": audio.url
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to download audio: HTTP {audio_response.status_code}",
                            "provider": "qwen3"
                        }
                else:
                    return {
                        "success": False,
                        "error": "No audio URL in response",
                        "provider": "qwen3"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Status: {response.status_code}, Message: {response.message}",
                    "provider": "qwen3"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "qwen3"
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
            import requests

            # 流式调用
            responses = MultiModalConversation.call(
                model='qwen3-tts-flash',
                text=text,
                voice=self.voice,
                language_type='Auto',
                stream=True
            )

            with open(output_path, 'wb') as f:
                for response in responses:
                    if response.status_code == 200:
                        audio = response.output.audio

                        # 流式返回的是 data 字段（base64 编码的音频块）
                        if audio.data:
                            # data 已经是 bytes 类型
                            f.write(audio.data)

                        # 最后一个响应包含完整的 URL
                        if audio.url:
                            # 可以选择使用 URL 或已写入的数据
                            pass
                    else:
                        return {
                            "success": False,
                            "error": f"Status: {response.status_code}",
                            "provider": "qwen3"
                        }

            return {
                "success": True,
                "output_path": output_path,
                "provider": "qwen3",
                "voice": self.voice,
                "mode": "streaming"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "qwen3"
            }

    def synthesize_stream_generator(self, text: str):
        """
        流式合成语音，返回音频数据生成器

        Args:
            text: 要转换的文本

        Yields:
            音频数据块 (bytes)
        """
        try:
            responses = MultiModalConversation.call(
                model='qwen3-tts-flash',
                text=text,
                voice=self.voice,
                language_type='Auto',
                stream=True
            )

            for response in responses:
                if response.status_code == 200:
                    audio = response.output.audio
                    if audio.data:
                        yield audio.data
                else:
                    raise Exception(f"TTS error: {response.status_code}")

        except Exception as e:
            raise Exception(f"Stream synthesis failed: {str(e)}")

    def get_available_voices(self) -> list:
        """
        获取可用的语音列表

        Returns:
            语音列表
        """
        # Qwen3 TTS Flash 支持的热门语音
        return [
            "Cherry",           # 芊悦 - 阳光积极、亲切自然小姐姐
            "Serena",          # 苏瑶 - 温柔小姐姐
            "Ethan",           # 晨煦 - 阳光、温暖、活力的男性
            "Chelsie",         # 千雪 - 二次元虚拟女友
            "Stella",          # 星辰 - 知性优雅女声
            "Lyra",            # 琳雅 - 清新甜美女声
            "Aria",            # 艾瑞 - 专业播音女声
            "Zoe",             # 佐伊 - 活泼可爱女声
            "Nova",            # 诺娃 - 科技感女声
            "Luna",            # 露娜 - 温柔治愈女声
            "Oliver",          # 奥利弗 - 成熟稳重男声
            "Leo",             # 里奥 - 年轻活力男声
            "Mason",           # 梅森 - 磁性低沉男声
            "Ryan",            # 瑞恩 - 专业播音男声
        ]
