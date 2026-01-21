import asyncio
import logging
import queue
import select
import signal
import sys
import time
import uuid
import wave
from typing import Optional, Dict, Any

import pyaudio

from schemas import AudioConfig, WSConnectConfig, DoubaoRealTimeConfig
from config import input_audio_config, output_audio_config, ws_connect_config, start_session_req
from client import RealtimeDialogClient
from mem import build_external_rag_payload, get_memory_instance

logger = logging.getLogger(__name__)


class AudioDeviceManager:
    """音频设备管理类，处理音频输入输出"""

    def __init__(self, input_config: AudioConfig = input_audio_config, output_config: AudioConfig = output_audio_config):
        self.input_config = input_config
        self.output_config = output_config
        self.pyaudio = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

    def open_input_stream(self) -> pyaudio.Stream:
        """打开音频输入流"""
        self.input_stream = self.pyaudio.open(
            format=self.input_config.bit_size,
            channels=self.input_config.channels,
            rate=self.input_config.sample_rate,
            input=True,
            frames_per_buffer=self.input_config.chunk
        )
        return self.input_stream

    def open_output_stream(self) -> pyaudio.Stream:
        """打开音频输出流"""
        self.output_stream = self.pyaudio.open(
            format=self.output_config.bit_size,
            channels=self.output_config.channels,
            rate=self.output_config.sample_rate,
            output=True,
            frames_per_buffer=self.output_config.chunk
        )
        return self.output_stream

    def cleanup(self) -> None:
        """清理音频设备资源"""
        for stream in [self.input_stream, self.output_stream]:
            if stream:
                stream.stop_stream()
                stream.close()
        self.pyaudio.terminate()


class DialogSession:
    """对话会话管理类"""
    is_audio_file_input: bool
    mod: str

    def __init__(
            self,
            ws_config: WSConnectConfig = ws_connect_config,
            session_config: DoubaoRealTimeConfig = start_session_req,
            output_audio_format: str = "pcm",
            audio_file_path: str = "",
            mod: str = "audio",
            memory_backend: str = "none",
            use_aec: bool = False
        ):
        self.use_aec = use_aec
        self.aec_audio: Optional[Any] = None

        self.use_memory = memory_backend.lower() != "none"
        if self.use_memory:
            self.memory_client = get_memory_instance(memory_backend)
            self.current_input = ""
            self.current_output = ""

        self.audio_file_path = audio_file_path
        self.is_audio_file_input = self.audio_file_path != ""
        if self.is_audio_file_input:
            mod = 'audio_file'
        else:
            self.say_hello_over_event = asyncio.Event()

            # AEC 仅在 macOS + pyobjc 可用时启用；否则回退到原 PyAudio
            self.audio_device: Optional[AudioDeviceManager] = None
            if self.use_aec and sys.platform == "darwin":
                try:
                    from audio_aec_macos import MacOSVPIOAudioIO, PCMFormat

                    in_fmt = PCMFormat(
                        sample_rate=int(input_audio_config.sample_rate),
                        channels=int(input_audio_config.channels),
                        sample_format="s16" if input_audio_config.bit_size == pyaudio.paInt16 else "f32",
                    )
                    out_fmt = PCMFormat(
                        sample_rate=int(output_audio_config.sample_rate),
                        channels=int(output_audio_config.channels),
                        sample_format="s16" if output_audio_config.bit_size == pyaudio.paInt16 else "f32",
                    )
                    self.aec_audio = MacOSVPIOAudioIO(
                        input_target=in_fmt,
                        output_source=out_fmt,
                        input_chunk_frames=int(input_audio_config.chunk),
                    )
                    logger.info("AEC enabled: macOS VPIO backend")
                except Exception as e:
                    logger.warning(f"AEC requested but macOS backend unavailable, fallback to PyAudio: {e}")
                    self.aec_audio = None

            if self.aec_audio is None:
                self.audio_device = AudioDeviceManager()
            # 录音线程
            self.is_recording = True
            # 播放线程
            self.is_playing = True
        self.mod = mod

        self.session_id = str(uuid.uuid4())
        if output_audio_format == "pcm_s16le":
            output_audio_config.format = "pcm_s16le"
            output_audio_config.bit_size = pyaudio.paInt16
        self.client = RealtimeDialogClient(
            ws_config=ws_config,
            session_config=session_config,
            session_id=self.session_id,
            output_audio_format=output_audio_format,
            mod=self.mod
        )

        # start
        self.is_running = True
        # finish
        self.is_session_finished = asyncio.Event()
        # 打断
        self.is_user_querying = False
        # tts or rag
        self.is_sending_tts_or_rag = False

        self.audio_queue = asyncio.Queue()
        
    def _audio_player_thread(self):
        """音频播放线程"""
        # 初始化音频队列和输出流
        assert self.audio_device is not None
        self.output_stream = self.audio_device.open_output_stream()
        try:
            while self.is_playing:
                try:
                    # 从队列获取音频数据
                    audio_data = self.audio_queue.get_nowait()
                    if audio_data is not None:
                        self.output_stream.write(audio_data)
                except asyncio.QueueEmpty:
                    # 队列为空时等待一小段时间
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"音频播放错误: {e}")
            raise e

    def _keyboard_input_thread(self, input_queue: queue.Queue) -> None:
        """在单独线程中监听标准输入（非阻塞）"""
        try:
            while self.is_running:
                # 使用 select 检查 stdin 是否有数据可读（超时 0.1 秒）
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if ready:
                    # 有数据可读时才读取
                    line = sys.stdin.readline()
                    if not line:
                        # 输入流关闭
                        input_queue.put(None)
                        break
                    input_str = line.strip()
                    if input_str:  # 只放入非空输入
                        input_queue.put(input_str)
                # 如果没有数据，循环会继续并检查 is_running
        except KeyboardInterrupt:
            logger.info("Keyboard input thread received interrupt, exiting...")
            input_queue.put(None)
        except Exception as e:
            logger.error(f"Input listener error: {e}")
            input_queue.put(None)
            raise e

    async def _inject_memory_once(self) -> None:
        if not self.use_memory:
            return
        try:
            profile = await self.memory_client.search_profile()
            recent_events = await self.memory_client.search_recent_events(1, 2)
            memory_summary = (
                "已知用户画像与近期事件：\n"
                f"Profile: {profile}\n"
                f"RecentEvents: {recent_events}"
            )
            items = [
                {"role": "user", "text": "记忆摘要"},
                {"role": "assistant", "text": memory_summary},
            ]
            await self.client.conversation_create(items)
        except Exception as e:
            logger.error(f"memory inject error: {e}")

    async def trigger_rag_for_query(self, query: str) -> None:
        if not self.use_memory:
            return
        external_rag = await build_external_rag_payload(
            memory_client=self.memory_client,
            query=query,
            max_items=2,
        )
        if external_rag and external_rag != "[]":
            await self.client.chat_rag_text(self.is_user_querying, external_rag)

    async def handle_server_response(self, response: Dict[str, Any]) -> None:
        if response == {}:
            return
        """处理服务器响应"""
        if response['message_type'] == 'SERVER_ACK' and isinstance(response.get('payload_msg'), bytes) and not self.is_sending_tts_or_rag:
            # logger.info(f"接收到音频数据: {len(response['payload_msg'])} 字节")
            audio_data = response['payload_msg']
            if not self.is_audio_file_input:
                if self.aec_audio is not None:
                    # AEC 生效需要“远端音频从本引擎播出”
                    await asyncio.to_thread(self.aec_audio.play_bytes, audio_data)
                else:
                    await self.audio_queue.put(audio_data)
            return
        elif response['message_type'] == 'SERVER_FULL_RESPONSE':
            logger.info(f"服务器响应: {response}")
            event = response.get('event')
            payload_msg = response.get('payload_msg', {})

            if event == 450:
                logger.info(f"清空缓存音频: {response['session_id']}")
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        continue
                # 打断
                self.is_user_querying = True

            if event == 350:
                tts_type = payload_msg.get("tts_type")
                # 原始闲聊不合适，默认只走RAG
                if tts_type in ["default"] and self.is_sending_tts_or_rag:
                    while not self.audio_queue.empty():
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            continue
                elif tts_type in ["external_rag", "chat_tts_text"]:
                    # 当为RAG和GTA的时候，接收音频
                    self.is_sending_tts_or_rag = False
                    if self.use_memory:
                        reply_id = payload_msg.get("reply_id")
                        if reply_id and self.current_input:
                            await self.memory_client.insert_message(
                                message_id=reply_id,
                                role="user",
                                content=self.current_input,
                                session_id=self.session_id
                            )

            if event == 451 and self.use_memory:
                results = payload_msg.get("results", [])
                extra = payload_msg.get("extra")
                if "endpoint" not in extra or bool(extra["endpoint"]) != True:
                    return
                # 用户说完话了，默认加入RAG，且不接收default音频
                self.current_input = results[0]["text"]
                logger.info(f"current input: {self.current_input}")
                self.is_sending_tts_or_rag = True
                asyncio.create_task(self.trigger_rag_for_query(self.current_input))

            if event == 459:
                # 解除打断
                self.is_user_querying = False

            if event == 553 and self.use_memory:
                self.is_sending_tts_or_rag = True
                asyncio.create_task(self.trigger_rag_for_query(self.current_input))

            if event == 550 and self.use_memory:
                content = payload_msg.get("content")
                reply_id = payload_msg.get("reply_id")
                if reply_id and content:
                    self.current_output += content

            if event == 359 and self.use_memory:
                reply_id = payload_msg.get("reply_id")
                if reply_id and self.current_output:
                    await self.memory_client.insert_message(
                        message_id=reply_id,
                        role="assistant",
                        content=self.current_output,
                        session_id=self.session_id
                    )
                    self.current_output = ""


        elif response['message_type'] == 'SERVER_ERROR':
            logger.error(f"服务器错误: {response['payload_msg']}")
            raise Exception("服务器错误")

    # async def trigger_chat_tts_text(self):
    #     """概率触发发送ChatTTSText请求"""
    #     if config.ENABLE_LOG:
    #         print("hit ChatTTSText event, start sending...")
    #     await self.client.chat_tts_text(
    #         is_user_querying=self.is_user_querying,
    #         start=True,
    #         end=False,
    #         content="emmm",
    #     )
    #     await self.client.chat_tts_text(
    #         is_user_querying=self.is_user_querying,
    #         start=False,
    #         end=True,
    #         content="",
    #     )

    async def receive_loop(self):
        try:
            while True:
                response = await self.client.receive_server_response()
                await self.handle_server_response(response)
                if 'event' in response and (response['event'] == 152 or response['event'] == 153):
                    logger.info(f"receive session finished event: {response['event']}")
                    self.is_session_finished.set()
                    break
                if 'event' in response and response['event'] == 359:
                    if self.is_audio_file_input:
                        logger.info(f"receive tts ended event")
                        self.is_session_finished.set()
                        break
                    else:
                        if not self.say_hello_over_event.is_set():
                            logger.info(f"SayHello over, input loop start...")
                            self.say_hello_over_event.set()
                        if self.mod == "text":
                            logger.info("请输入内容：")

        except asyncio.CancelledError:
            logger.info("接收任务已取消")
        except Exception as e:
            logger.error(f"接收消息错误: {e}")
        finally:
            self.stop()
            self.is_session_finished.set()

    async def process_text_input(self) -> None:
        await self.client.say_hello()
        await self.say_hello_over_event.wait()
        """主逻辑：处理文本输入和WebSocket通信"""
        # 确保连接最终关闭
        loop = asyncio.get_running_loop()
        try:
            # 启动输入监听线程
            input_queue = queue.Queue()
            loop.run_in_executor(None, self._keyboard_input_thread, input_queue)
            # 主循环：处理输入和上下文结束
            while self.is_running:
                try:
                    # 检查是否有输入（非阻塞）
                    input_str = input_queue.get_nowait()
                    if input_str is None:
                        # 输入流关闭
                        logger.info("Input channel closed")
                        break
                    if input_str:
                        if self.use_memory:
                            self.current_input = input_str
                        # 发送输入内容
                        await self.client.chat_text_query(input_str)
                except queue.Empty:
                    # 无输入时短暂休眠
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Text loop error: {e}")
            raise e

    async def process_microphone_input(self) -> None:
        await self.client.say_hello()
        logger.debug("waiting say_hello_over_event before mic start...")
        await self.say_hello_over_event.wait()
        logger.debug("say_hello_over_event set, mic loop starting...")
        """处理麦克风输入"""
        stream = None
        if self.aec_audio is not None:
            self.aec_audio.start()
            logger.info("已打开麦克风(AEC/VPIO)，请讲话...")
        else:
            assert self.audio_device is not None
            stream = self.audio_device.open_input_stream()
            logger.info("已打开麦克风，请讲话...")

        try:
            sent_chunks = 0
            last_log_ts = time.time()
            while self.is_recording:
                if self.aec_audio is not None:
                    audio_data = await asyncio.to_thread(self.aec_audio.get_mic_bytes, 1.0)
                    if audio_data:
                        await self.client.task_request(audio_data)
                        sent_chunks += 1
                        now = time.time()
                        if sent_chunks <= 5 or (now - last_log_ts) > 5:
                            logger.info(f"mic->server (AEC) chunk_bytes={len(audio_data)} sent={sent_chunks}")
                            last_log_ts = now
                else:
                    assert stream is not None
                    # 添加exception_on_overflow=False参数来忽略溢出错误
                    audio_data = await asyncio.to_thread(stream.read, input_audio_config.chunk, exception_on_overflow=False)
                    await self.client.task_request(audio_data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Microphone loop error: {e}")
            raise e

    async def process_audio_file_input(self, audio_file_path: str) -> None:
        # 读取WAV文件
        with wave.open(audio_file_path, 'rb') as wf:
            chunk_size = input_audio_config.chunk
            framerate = wf.getframerate()  # 采样率（如16000Hz）
            # 时长 = chunkSize（帧数） ÷ 采样率（帧/秒）
            sleep_seconds = chunk_size / framerate
            logger.info(f"开始处理音频文件: {audio_file_path}")

            # 分块读取并发送音频数据
            while True:
                audio_data = wf.readframes(chunk_size)
                if not audio_data:
                    break  # 文件读取完毕

                await self.client.task_request(audio_data)
                # sleep与chunk对应的音频时长一致，模拟实时输入
                await asyncio.sleep(sleep_seconds)

            logger.info(f"音频文件处理完成，等待服务器响应...")

    async def process_silence_audio(self) -> None:
        """发送静音音频"""
        silence_data = b'\x00' * 320
        await self.client.task_request(silence_data)

    async def start(self) -> None:
        """启动对话会话"""
        loop = asyncio.get_running_loop()
        signal.signal(signal.SIGINT, self._keyboard_signal)
        try:
            if not self.is_audio_file_input:
                if self.aec_audio is None:
                    loop.run_in_executor(None, self._audio_player_thread)
                else:
                    # 文本模式也需要能播出声音；仅播放时不安装麦克风 tap
                    if self.mod == "text":
                        await asyncio.to_thread(self.aec_audio.start, True)

            await self.client.connect()

            if self.use_memory:
                await self._inject_memory_once()

            if self.mod == "text":
                asyncio.create_task(self.receive_loop())
                asyncio.create_task(self.process_text_input())
            else:
                if self.is_audio_file_input:
                    asyncio.create_task(self.receive_loop())
                    asyncio.create_task(self.process_audio_file_input(self.audio_file_path))
                else:
                    asyncio.create_task(self.receive_loop())
                    asyncio.create_task(self.process_microphone_input())

            while self.is_running:
                await asyncio.sleep(0.1)
            await self.client.finish_session()
            await self.is_session_finished.wait()
            await self.client.finish_connection()
            await asyncio.sleep(0.1)
            await self.client.close()

            if self.use_memory:
                await self.memory_client.save_messages(self.session_id)

            logger.info(f"dialog request logid: {self.client.logid}, chat mod: {self.mod}")
        except Exception as e:
            logger.error(f"会话错误: {e}")
            self.stop()
            await asyncio.sleep(1)
        finally:
            if not self.is_audio_file_input:
                if self.aec_audio is not None:
                    try:
                        self.aec_audio.stop()
                    except Exception:
                        pass
                if self.audio_device is not None:
                    self.audio_device.cleanup()

    def stop(self):
        logger.info("Stopping DialogSession...")
        self.is_recording = False
        self.is_playing = False
        self.is_running = False

        if self.aec_audio is not None:
            try:
                self.aec_audio.stop()
            except Exception:
                pass
    
    def _keyboard_signal(self, sig, frame):
        logger.info(f"Receive keyboard Ctrl+C, initiating shutdown...")
        self.stop()