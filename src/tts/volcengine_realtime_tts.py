"""
火山引擎实时 TTS 客户端 - 支持流式文本输入和流式音频输出
使用 WebSocket 双向流式连接，真正的实时语音合成
"""
import asyncio
import json
import uuid
import websockets
import threading
import queue
import time
import sys
import os

sys.path.append("src/tts/protocols")

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


class VolcengineRealtimeTTS:
    """火山引擎实时 TTS 客户端"""

    def __init__(self, app_id: str, access_token: str, voice: str = "zh_female_cancan_mars_bigtts"):
        """
        初始化实时 TTS 客户端

        Args:
            app_id: 应用 ID
            access_token: Access Token
            voice: 音色
        """
        self.app_id = app_id
        self.access_token = access_token
        self.voice = voice
        self.endpoint = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

        self.websocket = None
        self.session_id = None
        self.audio_queue = None
        self.is_connected = False
        self.is_session_active = False

        self.first_audio_received = False
        self.start_time = None
        self.first_audio_delay = 0

        # 事件循环
        self.loop = None
        self.loop_thread = None

    def get_resource_id(self) -> str:
        """获取 Resource ID"""
        # Mars BigTTS 音色使用标准 Resource ID
        if self.voice.startswith("zh_") and "mars_bigtts" in self.voice:
            return "volc.service_type.10029"
        # BV 开头的是 Seed2 音色，使用 megatts
        elif self.voice.startswith("BV") or self.voice.startswith("S_"):
            return "volc.megatts.default"
        # 默认使用标准 Resource ID
        return "volc.service_type.10029"

    def _run_event_loop(self):
        """在独立线程中运行事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _start_event_loop(self):
        """启动事件循环线程"""
        if self.loop_thread is None or not self.loop_thread.is_alive():
            self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self.loop_thread.start()
            # 等待循环启动
            while self.loop is None:
                time.sleep(0.01)

    def _run_coroutine(self, coro):
        """在事件循环中运行协程"""
        if self.loop is None:
            self._start_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    async def _connect_async(self):
        """异步连接到 WebSocket"""
        headers = {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.get_resource_id(),
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

        self.websocket = await websockets.connect(
            self.endpoint,
            additional_headers=headers,
            max_size=10 * 1024 * 1024
        )

        # 启动连接
        await start_connection(self.websocket)
        await wait_for_event(
            self.websocket, MsgType.FullServerResponse, EventType.ConnectionStarted
        )

        self.is_connected = True
        # print('[火山引擎实时TTS] WebSocket 连接已建立')  # 静默

    async def _start_session_async(self):
        """异步启动会话"""
        base_request = {
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "namespace": "BidirectionalTTS",
            "req_params": {
                "speaker": self.voice,
                "audio_params": {
                    "format": "pcm",  # 使用 PCM 格式避免电流声（MP3 格式会导致播放器解析错误）
                    "sample_rate": 24000,
                    "enable_timestamp": True,
                },
                "additions": json.dumps({
                    "disable_markdown_filter": False,
                }),
            },
        }

        start_session_request = base_request.copy()
        start_session_request["event"] = EventType.StartSession
        self.session_id = str(uuid.uuid4())

        await start_session(
            self.websocket,
            json.dumps(start_session_request).encode(),
            self.session_id
        )
        await wait_for_event(
            self.websocket, MsgType.FullServerResponse, EventType.SessionStarted
        )

        self.is_session_active = True
        # print(f'[火山引擎实时TTS] 会话已启动: {self.session_id}')  # 静默

    async def _send_text_async(self, text: str):
        """异步发送文本"""
        if not self.is_session_active:
            raise RuntimeError("会话未启动")

        base_request = {
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "namespace": "BidirectionalTTS",
            "req_params": {
                "speaker": self.voice,
                "audio_params": {
                    "format": "pcm",  # 使用 PCM 格式避免电流声（MP3 格式会导致播放器解析错误）
                    "sample_rate": 24000,
                    "enable_timestamp": True,
                },
                "additions": json.dumps({
                    "disable_markdown_filter": False,
                }),
                "text": text,
            },
        }

        synthesis_request = base_request.copy()
        synthesis_request["event"] = EventType.TaskRequest

        await task_request(
            self.websocket,
            json.dumps(synthesis_request).encode(),
            self.session_id
        )

    async def _receive_audio_async(self):
        """异步接收音频数据"""
        while self.is_session_active or not self.audio_queue.empty():
            try:
                msg = await asyncio.wait_for(receive_message(self.websocket), timeout=1.0)

                if msg.type == MsgType.FullServerResponse:
                    if msg.event == EventType.SessionFinished:
                        # 会话结束
                        self.is_session_active = False
                        # 等待一小段时间确保所有音频都收到
                        await asyncio.sleep(0.5)
                        self.audio_queue.put(None)  # 结束信号
                        break
                    elif msg.event == EventType.TTSSentenceStart:
                        if not self.first_audio_received:
                            self.start_time = time.time()
                elif msg.type == MsgType.AudioOnlyServer:
                    audio_data = msg.payload
                    if audio_data:
                        self.audio_queue.put(audio_data)

                        if not self.first_audio_received:
                            self.first_audio_received = True
                            if self.start_time:
                                self.first_audio_delay = time.time() - self.start_time
                                # print(f'[火山引擎实时TTS] 首个音频块延迟: {self.first_audio_delay:.3f}秒')  # 静默
                elif msg.type == MsgType.Error:
                    error_msg = msg.payload.decode('utf-8') if isinstance(msg.payload, bytes) else str(msg.payload)
                    # print(f'❌ TTS 错误: {error_msg}')  # 静默
                    self.audio_queue.put(None)
                    break
            except asyncio.TimeoutError:
                # 如果会话已结束且超时，说明没有更多数据了
                if not self.is_session_active:
                    self.audio_queue.put(None)
                    break
                continue
            except Exception as e:
                # 断开连接时的错误是正常的，静默处理
                # print(f'❌ TTS 接收错误: {e}')  # 静默
                self.audio_queue.put(None)
                break

    async def _finish_session_async(self):
        """异步结束会话"""
        if self.is_session_active:
            await finish_session(self.websocket, self.session_id)
            # 注意：不要在这里设置 is_session_active = False
            # 让接收循环在收到 SessionFinished 事件时再设置
            # print('[火山引擎实时TTS] 会话结束信号已发送')  # 静默

    async def _disconnect_async(self):
        """异步断开连接"""
        if self.is_connected and self.websocket:
            try:
                # 先标记为未连接，停止接收循环
                self.is_connected = False

                # 发送断开请求（但不等待响应，避免与接收循环冲突）
                try:
                    await finish_connection(self.websocket)
                except Exception:
                    pass  # 忽略发送错误

                # 直接关闭 WebSocket
                await self.websocket.close()
                # print('[火山引擎实时TTS] 连接已关闭')  # 静默
            except Exception as e:
                # print(f'❌ TTS 断开连接时出错: {e}')  # 静默
                self.is_connected = False

    def start_session(self, audio_format: str = "pcm", sample_rate: int = 24000) -> queue.Queue:
        """
        启动实时 TTS 会话

        Args:
            audio_format: 音频格式 (pcm)
            sample_rate: 采样率

        Returns:
            音频数据队列
        """
        self._start_event_loop()

        # 如果有旧的接收任务，先取消
        if hasattr(self, 'receive_task') and self.receive_task:
            try:
                self.receive_task.cancel()
            except:
                pass

        # 创建新的音频队列（每次对话创建新队列）
        self.audio_queue = queue.Queue()

        # 只在未连接时才建立 WebSocket 连接（复用连接）
        if not self.is_connected:
            self._run_coroutine(self._connect_async())

        # 启动新会话
        self._run_coroutine(self._start_session_async())

        # 启动接收线程（保存引用以便清理）
        self.receive_task = asyncio.run_coroutine_threadsafe(
            self._receive_audio_async(), self.loop
        )

        self.start_time = time.time()

        return self.audio_queue

    def send_text(self, text: str):
        """
        发送文本进行合成

        Args:
            text: 要合成的文本
        """
        if not self.is_session_active:
            raise RuntimeError("会话未启动，请先调用 start_session()")

        self._run_coroutine(self._send_text_async(text))

    def finish(self):
        """结束会话（但保持连接以便复用）"""
        if self.is_session_active:
            self._run_coroutine(self._finish_session_async())

    def clear_queue(self):
        """清空音频队列（用于打断）"""
        if self.audio_queue:
            # 清空队列中的所有数据
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except:
                    break
            # 放入结束信号
            self.audio_queue.put(None)

    def disconnect(self):
        """断开连接"""
        if self.is_connected:
            self._run_coroutine(self._disconnect_async())

            # 等待接收任务完成（带超时）
            if hasattr(self, 'receive_task'):
                try:
                    self.receive_task.result(timeout=2.0)
                except Exception:
                    pass  # 忽略接收任务的错误

        # 停止事件循环
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            # 等待事件循环停止
            import time
            time.sleep(0.1)

    def get_metrics(self) -> dict:
        """获取性能指标"""
        return {
            "session_id": self.session_id,
            "first_audio_delay": self.first_audio_delay,
            "voice": self.voice
        }

    def get_available_voices(self) -> list:
        """获取可用的语音列表"""
        return [
            "zh_female_cancan_mars_bigtts",          # 灿灿女声
            "zh_male_aojiaobazong_mars_bigtts",      # 霸总男声
            "zh_female_wanwanxiaohe_mars_bigtts",    # 婉婉小和
            "zh_male_qingxinnansheng_mars_bigtts",   # 清新男声
        ]
