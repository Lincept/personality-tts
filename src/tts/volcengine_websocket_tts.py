"""
火山引擎 TTS - 基于官方 WebSocket API
简化版：用于基本的文本转语音
"""
import asyncio
import json
import uuid
import websockets
import logging
from typing import Optional

# 复制官方的 protocols 模块
import sys
import os
sys.path.append("/Users/shangguangtao/Downloads/volcengine_bidirection_demo")

from protocols import (
    EventType,
    MsgType,
    finish_connection,
    finish_session,
    receive_message,
    start_connection,
    start_session,
    task_request,
    wait_for_event,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VolcengineWebSocketTTS:
    """火山引擎 WebSocket TTS 客户端"""

    def __init__(self, app_id: str, api_key: str = None, access_token: str = None, voice: str = "zh_female_tianmei"):
        """
        初始化客户端

        Args:
            app_id: 应用 ID
            api_key: API Key (兼容旧版)
            access_token: Access Token (推荐使用)
            voice: 音色
        """
        self.app_id = app_id
        # 优先使用 access_token，如果没有则使用 api_key
        self.access_token = access_token if access_token else api_key
        self.voice = voice
        self.endpoint = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

    def get_resource_id(self) -> str:
        """获取 Resource ID"""
        # BV 开头的是 Seed2 音色，使用 megatts
        if self.voice.startswith("BV") or self.voice.startswith("S_"):
            return "volc.megatts.default"
        # zh_ 开头的是普通音色
        return "volc.service_type.10029"

    async def synthesize_async(self, text: str, output_path: str) -> dict:
        """
        异步合成语音

        Args:
            text: 要转换的文本
            output_path: 输出文件路径

        Returns:
            结果字典
        """
        try:
            # 连接 WebSocket
            headers = {
                "X-Api-App-Key": self.app_id,
                "X-Api-Access-Key": self.access_token,
                "X-Api-Resource-Id": self.get_resource_id(),
                "X-Api-Connect-Id": str(uuid.uuid4()),
            }

            logger.info(f"Connecting to {self.endpoint}")
            websocket = await websockets.connect(
                self.endpoint,
                additional_headers=headers,
                max_size=10 * 1024 * 1024
            )
            logger.info("Connected to WebSocket server")

            try:
                # 启动连接
                await start_connection(websocket)
                await wait_for_event(
                    websocket, MsgType.FullServerResponse, EventType.ConnectionStarted
                )

                # 准备请求参数
                base_request = {
                    "user": {
                        "uid": str(uuid.uuid4()),
                    },
                    "namespace": "BidirectionalTTS",
                    "req_params": {
                        "speaker": self.voice,
                        "audio_params": {
                            "format": "mp3",
                            "sample_rate": 24000,
                            "enable_timestamp": True,
                        },
                        "additions": json.dumps({
                            "disable_markdown_filter": False,
                        }),
                    },
                }

                # 启动会话
                start_session_request = base_request.copy()
                start_session_request["event"] = EventType.StartSession
                session_id = str(uuid.uuid4())

                await start_session(
                    websocket,
                    json.dumps(start_session_request).encode(),
                    session_id
                )
                await wait_for_event(
                    websocket, MsgType.FullServerResponse, EventType.SessionStarted
                )

                # 发送文本
                synthesis_request = base_request.copy()
                synthesis_request["event"] = EventType.TaskRequest
                synthesis_request["req_params"]["text"] = text

                await task_request(
                    websocket,
                    json.dumps(synthesis_request).encode(),
                    session_id
                )

                # 结束会话
                await finish_session(websocket, session_id)

                # 接收音频数据
                audio_data = bytearray()
                while True:
                    msg = await receive_message(websocket)

                    if msg.type == MsgType.FullServerResponse:
                        if msg.event == EventType.SessionFinished:
                            break
                    elif msg.type == MsgType.AudioOnlyServer:
                        audio_data.extend(msg.payload)
                    elif msg.type == MsgType.Error:
                        raise RuntimeError(f"TTS error: {msg}")

                # 保存音频文件
                if audio_data:
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    logger.info(f"Audio saved: {len(audio_data)} bytes -> {output_path}")

                    return {
                        "success": True,
                        "output_path": output_path,
                        "provider": "volcengine_websocket",
                        "voice": self.voice,
                        "text_length": len(text),
                        "audio_size": len(audio_data)
                    }
                else:
                    return {
                        "success": False,
                        "error": "No audio data received",
                        "provider": "volcengine_websocket"
                    }

            finally:
                # 关闭连接
                await finish_connection(websocket)
                await wait_for_event(
                    websocket, MsgType.FullServerResponse, EventType.ConnectionFinished
                )
                await websocket.close()
                logger.info("Connection closed")

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "volcengine_websocket"
            }

    def synthesize(self, text: str, output_path: str) -> dict:
        """
        同步合成语音（包装异步方法）

        Args:
            text: 要转换的文本
            output_path: 输出文件路径

        Returns:
            结果字典
        """
        return asyncio.run(self.synthesize_async(text, output_path))


# 测试代码
if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.config_loader import ConfigLoader

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()
    volcengine_config = config.get("volcengine_seed2", {})

    # 创建客户端
    tts = VolcengineWebSocketTTS(
        app_id=volcengine_config.get("app_id"),
        api_key=volcengine_config.get("api_key"),
        access_token=volcengine_config.get("access_token"),
        voice="zh_female_tianmei"
    )

    # 测试
    result = tts.synthesize("学弟，今天过得怎么样？", "data/audios/volcengine_ws_test.mp3")
    print(f"\n结果: {result}")
