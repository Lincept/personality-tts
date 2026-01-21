import gzip
import logging
import json
from typing import Dict, Any
from dataclasses import asdict

import websockets
from client import protocol
from schemas import WSConnectConfig, DoubaoRealTimeConfig



logger = logging.getLogger(__name__)
class RealtimeDialogClient:
    def __init__(self, ws_config: WSConnectConfig, session_config: DoubaoRealTimeConfig, session_id: str, output_audio_format: str = "pcm",
                 mod: str = "audio") -> None:
        self.ws_config = ws_config
        self.session_config = session_config
        self.logid = None
        self.session_id = session_id
        self.output_audio_format = output_audio_format
        self.mod = mod
        self.ws: websockets.ClientConnection = None # type: ignore

    async def connect(self) -> None:
        """建立WebSocket连接"""
        safe_headers = dict(self.ws_config.headers or {})
        if 'X-Api-Access-Key' in safe_headers and safe_headers['X-Api-Access-Key']:
            ak = str(safe_headers['X-Api-Access-Key'])
            safe_headers['X-Api-Access-Key'] = ak[:4] + "***" + ak[-4:]
        logger.info(f"url: {self.ws_config.base_url}, headers: {safe_headers}")
        # Use 'additional_headers' to pass headers through websockets without triggering create_connection kwargs error
        self.ws = await websockets.connect(
            self.ws_config.base_url,
            additional_headers=self.ws_config.headers,
            ping_interval=None
        )
        # Get handshake response header 'X-Tt-Logid' in a version-robust way.
        self.logid = None
        try:
            # Common attribute on some websockets versions
            if hasattr(self.ws, 'response_headers') and self.ws.response_headers: # type: ignore
                try:
                    self.logid = self.ws.response_headers.get('X-Tt-Logid') # type: ignore
                except Exception:
                    try:
                        self.logid = self.ws.response_headers['X-Tt-Logid'] # type: ignore
                    except Exception:
                        pass
            # Some implementations expose a 'response' object with headers (e.g., aiohttp-like)
            elif hasattr(self.ws, 'response') and self.ws.response is not None:
                resp = self.ws.response
                if hasattr(resp, 'headers'):
                    self.logid = resp.headers.get('X-Tt-Logid')
                elif hasattr(resp, 'getheader'):
                    self.logid = resp.getheader('X-Tt-Logid') # type: ignore
        except Exception:
            # Ignore errors reading headers; leave logid as None
            self.logid = None

        logger.info(f"dialog server response logid: {self.logid}")

        # StartConnection request
        start_connection_request = bytearray(protocol.generate_header())
        start_connection_request.extend(int(1).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        start_connection_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        start_connection_request.extend(payload_bytes)
        await self.ws.send(start_connection_request)
        response = await self.ws.recv()
        logger.info(f"StartConnection response: {protocol.parse_response(response)}")

        # 这个参数，在text或者audio_file模式，可以在一段时间内保持静默
        self.session_config.dialog["extra"]["input_mod"] = self.mod
        # StartSession request
        if self.output_audio_format == "pcm_s16le":
            self.session_config.tts["audio_config"]["format"] = "pcm_s16le"
        payload_bytes = str.encode(json.dumps(asdict(self.session_config)))
        payload_bytes = gzip.compress(payload_bytes)
        start_session_request = bytearray(protocol.generate_header())
        start_session_request.extend(int(100).to_bytes(4, 'big'))
        start_session_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        start_session_request.extend(str.encode(self.session_id))
        start_session_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        start_session_request.extend(payload_bytes)
        await self.ws.send(start_session_request)
        response = await self.ws.recv()
        logger.info(f"StartSession response: {protocol.parse_response(response)}")

    async def say_hello(self) -> None:
        """发送Hello消息"""
        payload = {
            "content": "你好，我是小雨，有什么可以帮助你的？",
        }
        hello_request = bytearray(protocol.generate_header())
        hello_request.extend(int(300).to_bytes(4, 'big'))
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)
        hello_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        hello_request.extend(str.encode(self.session_id))
        hello_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        hello_request.extend(payload_bytes)
        await self.ws.send(hello_request)

    async def chat_text_query(self, content: str) -> None:
        """发送Chat Text Query消息"""
        payload = {
            "content": content,
        }
        chat_text_query_request = bytearray(protocol.generate_header())
        chat_text_query_request.extend(int(501).to_bytes(4, 'big'))
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)
        chat_text_query_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        chat_text_query_request.extend(str.encode(self.session_id))
        chat_text_query_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        chat_text_query_request.extend(payload_bytes)
        await self.ws.send(chat_text_query_request)

    async def chat_tts_text(self, is_user_querying: bool, start: bool, end: bool, content: str) -> None:
        if is_user_querying:
            return
        """发送Chat TTS Text消息"""
        payload = {
            "start": start,
            "end": end,
            "content": content,
        }
        logger.info(f"ChatTTSTextRequest payload: {payload}")
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)

        chat_tts_text_request = bytearray(protocol.generate_header())
        chat_tts_text_request.extend(int(500).to_bytes(4, 'big'))
        chat_tts_text_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        chat_tts_text_request.extend(str.encode(self.session_id))
        chat_tts_text_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        chat_tts_text_request.extend(payload_bytes)
        await self.ws.send(chat_tts_text_request)

    async def chat_rag_text(self, is_user_querying: bool, external_rag: str) -> None:
        if is_user_querying:
            return
        """发送Chat TTS Text消息"""
        payload = {
            "external_rag": external_rag,
        }
        logger.info(f"ChatRAGTextRequest payload: {payload}")
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)

        chat_rag_text_request = bytearray(protocol.generate_header())
        chat_rag_text_request.extend(int(502).to_bytes(4, 'big'))
        chat_rag_text_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        chat_rag_text_request.extend(str.encode(self.session_id))
        chat_rag_text_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        chat_rag_text_request.extend(payload_bytes)
        await self.ws.send(chat_rag_text_request)

    async def conversation_create(self, items: list[Dict[str, Any]]) -> None:
        """发送ConversationCreate消息（初始化上下文）"""
        payload = {
            "items": items,
        }
        logger.info(f"ConversationCreate payload: {payload}")
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)

        conversation_create_request = bytearray(protocol.generate_header())
        conversation_create_request.extend(int(510).to_bytes(4, 'big'))
        conversation_create_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        conversation_create_request.extend(str.encode(self.session_id))
        conversation_create_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        conversation_create_request.extend(payload_bytes)
        await self.ws.send(conversation_create_request)

    async def task_request(self, audio: bytes) -> None:
        task_request = bytearray(
            protocol.generate_header(message_type=protocol.CLIENT_AUDIO_ONLY_REQUEST,
                                     serial_method=protocol.NO_SERIALIZATION))
        task_request.extend(int(200).to_bytes(4, 'big'))
        task_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        task_request.extend(str.encode(self.session_id))
        payload_bytes = gzip.compress(audio)
        task_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
        task_request.extend(payload_bytes)
        await self.ws.send(task_request)

    async def receive_server_response(self) -> Dict[str, Any]:
        try:
            # 检查连接是否存在
            if self.ws is None:
                raise Exception("WebSocket connection is not initialized")
            
            response = await self.ws.recv()
            data = protocol.parse_response(response)
            return data
        except Exception as e:
            raise Exception(f"Failed to receive message: {e}")

    async def finish_session(self):
        finish_session_request = bytearray(protocol.generate_header())
        finish_session_request.extend(int(102).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        finish_session_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        finish_session_request.extend(str.encode(self.session_id))
        finish_session_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        finish_session_request.extend(payload_bytes)
        await self.ws.send(finish_session_request)

    async def finish_connection(self):
        finish_connection_request = bytearray(protocol.generate_header())
        finish_connection_request.extend(int(2).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        finish_connection_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        finish_connection_request.extend(payload_bytes)
        await self.ws.send(finish_connection_request)
        response = await self.ws.recv()
        logger.info(f"FinishConnection response: {protocol.parse_response(response)}")

    async def close(self) -> None:
        """关闭WebSocket连接"""
        if self.ws:
            logger.info(f"Closing WebSocket connection...")
            await self.ws.close()