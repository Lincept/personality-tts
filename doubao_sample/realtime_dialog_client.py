import asyncio
import json
import gzip
import random
from typing import Dict, Any
import websockets
import protocol
import config
from timer import timer


class RealtimeDialogClient:
    """实时对话客户端，处理WebSocket通信"""
    
    def __init__(self, recv_timeout: int = 30, mod: str = "text", output_audio_format: str = "pcm", ws_config: Dict[str, Any] = None, session_id: str = ""):
        self.recv_timeout = recv_timeout
        self.mod = mod
        self.output_audio_format = output_audio_format
        self.config = ws_config or config.ws_connect_config
        self.session_id = session_id or self._generate_session_id()
        self.ws = None

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        import uuid
        return str(uuid.uuid4())

    async def connect(self) -> None:
        """建立WebSocket连接"""
        timer.start("connect")
        if config.ENABLE_LOG:
            print(f"url: {self.config['base_url']}, headers: {self.config['headers']}")
        
        self.ws = await websockets.connect(
            self.config['base_url'],
            extra_headers=self.config['headers'],
            ping_interval=20,
            ping_timeout=10
        )
        
        # StartConnection request
        start_connection_request = bytearray(protocol.generate_header())
        start_connection_request.extend(int(101).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        start_connection_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        start_connection_request.extend(payload_bytes)
        await self.ws.send(start_connection_request)
        response = await self.ws.recv()
        if config.ENABLE_LOG:
            print(f"StartConnection response: {protocol.parse_response(response)}")

        # 扩大这个参数，可以在一段时间内保持静默，主要用于text模式，参数范围[10,120]
        config.start_session_req["dialog"]["extra"]["recv_timeout"] = self.recv_timeout
        # 这个参数，在text或者audio_file模式，可以在一段时间内保持静默
        config.start_session_req["dialog"]["extra"]["input_mod"] = self.mod
        # StartSession request
        if self.output_audio_format == "pcm_s16le":
            config.start_session_req["tts"]["audio_config"]["format"] = "pcm_s16le"
        request_params = config.start_session_req
        payload_bytes = str.encode(json.dumps(request_params))
        payload_bytes = gzip.compress(payload_bytes)
        start_session_request = bytearray(protocol.generate_header())
        start_session_request.extend(int(100).to_bytes(4, 'big'))
        start_session_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        start_session_request.extend(str.encode(self.session_id))
        start_session_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        start_session_request.extend(payload_bytes)
        await self.ws.send(start_session_request)
        response = await self.ws.recv()
        if config.ENABLE_LOG:
            print(f"StartSession response: {protocol.parse_response(response)}")
        timer.end("connect")

    async def say_hello(self) -> None:
        """发送Hello消息"""
        payload = {
            "content": "你好，我是小雨，有什么可以帮助你的？",
        }
        hello_request = bytearray(protocol.generate_header())
        hello_request.extend(int(104).to_bytes(4, 'big'))
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)
        hello_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        hello_request.extend(str.encode(self.session_id))
        hello_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        hello_request.extend(payload_bytes)
        await self.ws.send(hello_request)

    async def chat_text_query(self, text: str) -> None:
        """发送文本查询"""
        payload = {
            "text": text,
        }
        chat_text_request = bytearray(protocol.generate_header())
        chat_text_request.extend(int(103).to_bytes(4, 'big'))
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)
        chat_text_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        chat_text_request.extend(str.encode(self.session_id))
        chat_text_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        chat_text_request.extend(payload_bytes)
        await self.ws.send(chat_text_request)

    async def chat_tts_text(self, is_user_querying: bool, start: bool, end: bool, content: str) -> None:
        """发送ChatTTSText请求"""
        payload = {
            "is_user_querying": is_user_querying,
            "start": start,
            "end": end,
            "content": content,
        }
        chat_tts_text_request = bytearray(protocol.generate_header())
        chat_tts_text_request.extend(int(301).to_bytes(4, 'big'))
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)
        chat_tts_text_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        chat_tts_text_request.extend(str.encode(self.session_id))
        chat_tts_text_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        chat_tts_text_request.extend(payload_bytes)
        await self.ws.send(chat_tts_text_request)

    async def chat_rag_text(self, is_user_querying: bool, start: bool, end: bool, content: str, external_rag: str = "") -> None:
        """发送ChatRAGText请求"""
        payload = {
            "is_user_querying": is_user_querying,
            "start": start,
            "end": end,
            "content": content,
            "external_rag": external_rag,
        }
        chat_rag_text_request = bytearray(protocol.generate_header())
        chat_rag_text_request.extend(int(502).to_bytes(4, 'big'))
        payload_bytes = str.encode(json.dumps(payload))
        payload_bytes = gzip.compress(payload_bytes)
        chat_rag_text_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        chat_rag_text_request.extend(str.encode(self.session_id))
        chat_rag_text_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        chat_rag_text_request.extend(payload_bytes)
        await self.ws.send(chat_rag_text_request)

    async def task_request(self, audio: bytes) -> None:
        """发送音频任务请求"""
        timer.start("audio_send_request", "audio_send")
        
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
        
        timer.end("audio_send_request", "audio_send")

    async def receive_server_response(self) -> Dict[str, Any]:
        """接收服务器响应"""
        timer.start("receive_server_response", "audio_receive")
        try:
            response = await self.ws.recv()
            data = protocol.parse_response(response)
            timer.end("receive_server_response", "audio_receive")
            return data
        except Exception as e:
            timer.end("receive_server_response", "audio_receive")
            raise Exception(f"Failed to receive message: {e}")

    async def finish_session(self):
        """结束会话"""
        finish_session_request = bytearray(protocol.generate_header())
        finish_session_request.extend(int(102).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        finish_session_request.extend((len(self.session_id)).to_bytes(4, 'big'))
        finish_session_request.extend(str.encode(self.session_id))
        finish_session_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        finish_session_request.extend(payload_bytes)
        await self.ws.send(finish_session_request)

    async def close(self):
        """关闭WebSocket连接"""
        if self.ws:
            await self.ws.close()