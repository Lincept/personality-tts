import asyncio
import queue
import random
import signal
import sys
import threading
import time
import uuid
import wave
from dataclasses import dataclass
from typing import Optional, Dict, Any

import pyaudio

import config
from memory_client import MemoryClient, MemorySettings, extract_assistant_text, extract_user_query_from_asr
from realtime_dialog_client import RealtimeDialogClient
from utils import timer

@dataclass
class AudioConfig:
    """音频配置数据类"""
    format: str
    bit_size: int
    channels: int
    sample_rate: int
    chunk: int


class AudioDeviceManager:
    """音频设备管理类，处理音频输入输出"""

    def __init__(self, input_config: AudioConfig, output_config: AudioConfig):
        self.input_config = input_config
        self.output_config = output_config
        self.pyaudio = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

    def open_input_stream(self) -> pyaudio.Stream:
        """打开音频输入流"""
        # p = pyaudio.PyAudio()
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

    def __init__(self, ws_config: Dict[str, Any], output_audio_format: str = "pcm", audio_file_path: str = "",
                 mod: str = "audio", recv_timeout: int = 10):
        self.audio_file_path = audio_file_path
        self.recv_timeout = recv_timeout
        self.is_audio_file_input = self.audio_file_path != ""
        if self.is_audio_file_input:
            mod = 'audio_file'
        else:
            self.say_hello_over_event = asyncio.Event()
        self.mod = mod

        self.session_id = str(uuid.uuid4())
        self.client = RealtimeDialogClient(config=ws_config, session_id=self.session_id,
                                           output_audio_format=output_audio_format, mod=mod, recv_timeout=recv_timeout)
        if output_audio_format == "pcm_s16le":
            config.output_audio_config["format"] = "pcm_s16le"
            config.output_audio_config["bit_size"] = pyaudio.paInt16

        self.is_running = True
        self.is_session_finished = False
        self.is_user_querying = False
        self.is_sending_chat_tts_text = False
        self.audio_buffer = b''

        self.last_asr_text: str = ""
        self.pending_user_turn: Optional[str] = None
        self.pending_assistant_text_parts: list[str] = []
        self.conversation_messages: list[Dict[str, str]] = []

        self.memory_client: Optional[MemoryClient] = None
        if getattr(config, "MEMORY_ENABLE", False):
            self.memory_client = MemoryClient(
                MemorySettings(
                    enable=True,
                    ak=getattr(config, "MEMORY_AK", ""),
                    sk=getattr(config, "MEMORY_SK", ""),
                    collection_name=getattr(config, "MEMORY_COLLECTION_NAME", ""),
                    user_id=getattr(config, "MEMORY_USER_ID", ""),
                    assistant_id=getattr(config, "MEMORY_ASSISTANT_ID", ""),
                    memory_types=list(getattr(config, "MEMORY_TYPES", []) or []),
                    limit=int(getattr(config, "MEMORY_LIMIT", 3)),
                    transition_words=str(getattr(config, "MEMORY_TRANSITION_WORDS", "根据你的历史记录：")),
                )
            )

        signal.signal(signal.SIGINT, self._keyboard_signal)
        self.audio_queue = queue.Queue()
        if not self.is_audio_file_input:
            self.audio_device = AudioDeviceManager(
                AudioConfig(**config.input_audio_config),
                AudioConfig(**config.output_audio_config)
            )
            # 初始化音频队列和输出流
            self.output_stream = self.audio_device.open_output_stream()
            # 启动播放线程
            self.is_recording = True
            self.is_playing = True
            self.player_thread = threading.Thread(target=self._audio_player_thread)
            self.player_thread.daemon = True
            self.player_thread.start()

    def _audio_player_thread(self):
        """音频播放线程"""
        while self.is_playing:
            try:
                # 从队列获取音频数据
                audio_data = self.audio_queue.get(timeout=1.0)
                if audio_data is not None:
                    self.output_stream.write(audio_data)
            except queue.Empty:
                # 队列为空时等待一小段时间
                time.sleep(0.1)
            except Exception as e:
                if config.ENABLE_LOG:
                    print(f"音频播放错误: {e}")
                time.sleep(0.1)

    def handle_server_response(self, response: Dict[str, Any]) -> None:
        if response == {}:
            return
        """处理服务器响应"""
        if response['message_type'] == 'SERVER_ACK' and isinstance(response.get('payload_msg'), bytes):
            # if config.ENABLE_LOG:
            #     print(f"\n接收到音频数据: {len(response['payload_msg'])} 字节")
            if self.is_sending_chat_tts_text:
                return
            audio_data = response['payload_msg']
            if not self.is_audio_file_input:
                self.audio_queue.put(audio_data)
            self.audio_buffer += audio_data
        elif response['message_type'] == 'SERVER_FULL_RESPONSE':
            if config.ENABLE_LOG:
                print(f"服务器响应: {response}")
            event = response.get('event')
            payload_msg = response.get('payload_msg', {})

            # 记录 ASR 文本（451: ASRResponse）
            if event == 451:
                text = extract_user_query_from_asr(payload_msg)
                if text:
                    self.last_asr_text = text

            # 记录助手文本（550: ChatResponse, 559: ChatEnded）
            if event == 550:
                text = extract_assistant_text(payload_msg)
                if text:
                    self.pending_assistant_text_parts.append(text)
            if event == 559:
                if self.pending_assistant_text_parts:
                    assistant_text = "".join(self.pending_assistant_text_parts).strip()
                    self.pending_assistant_text_parts.clear()
                    if assistant_text:
                        self.conversation_messages.append({"role": "assistant", "content": assistant_text})

            if event == 450:
                if config.ENABLE_LOG:
                    print(f"清空缓存音频: {response['session_id']}")
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        continue
                self.is_user_querying = True

            if event == 350 and self.is_sending_chat_tts_text and payload_msg.get("tts_type") in ["chat_tts_text", "external_rag"]:
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        continue
                self.is_sending_chat_tts_text = False

            if event == 459:
                self.is_user_querying = False
                user_text = (self.last_asr_text or "").strip()
                if user_text:
                    self.conversation_messages.append({"role": "user", "content": user_text})
                # 触发外部 RAG：这里接入 Viking 长期记忆检索
                if self.memory_client is not None and user_text:
                    asyncio.create_task(self.trigger_memory_rag(user_text))
        elif response['message_type'] == 'SERVER_ERROR':
            if config.ENABLE_LOG:
                print(f"服务器错误: {response['payload_msg']}")
            raise Exception("服务器错误")

    async def trigger_chat_tts_text(self):
        """概率触发发送ChatTTSText请求"""
        if config.ENABLE_LOG:
            print("hit ChatTTSText event, start sending...")
        await self.client.chat_tts_text(
            is_user_querying=self.is_user_querying,
            start=True,
            end=False,
            content="emmm",
        )
        await self.client.chat_tts_text(
            is_user_querying=self.is_user_querying,
            start=False,
            end=True,
            content="",
        )

    async def trigger_chat_rag_text(self):
        await asyncio.sleep(0) # 模拟查询外部RAG的耗时，这里为了不影响GTA安抚话术的播报，直接sleep 5秒
        if config.ENABLE_LOG:
            print("hit ChatRAGText event, start sending...")

    async def trigger_memory_rag(self, user_text: str) -> None:
        if self.memory_client is None:
            return
        try:
            external_rag = await self.memory_client.search_external_rag(user_text)
        except Exception as e:
            if config.ENABLE_LOG:
                print(f"memory search failed: {e}")
            return

        if not external_rag:
            return

        # 将记忆作为 external_rag 注入服务端上下文
        await self.client.chat_rag_text(self.is_user_querying, external_rag=external_rag)

    def _keyboard_signal(self, sig, frame):
        if config.ENABLE_LOG:
            print(f"receive keyboard Ctrl+C")
        self.stop()

    def stop(self):
        self.is_recording = False
        self.is_playing = False
        self.is_running = False

    async def receive_loop(self):
        try:
            while True:
                response = await self.client.receive_server_response()
                self.handle_server_response(response)
                if 'event' in response and (response['event'] == 152 or response['event'] == 153):
                    if config.ENABLE_LOG:
                        print(f"receive session finished event: {response['event']}")
                    self.is_session_finished = True
                    break
                if 'event' in response and response['event'] == 359:
                    if self.is_audio_file_input:
                        if config.ENABLE_LOG:
                            print(f"receive tts ended event")
                        self.is_session_finished = True
                        break
                    else:
                        if not self.say_hello_over_event.is_set():
                            if config.ENABLE_LOG:
                                print(f"receive tts sayhello ended event")
                            self.say_hello_over_event.set()
                        if self.mod == "text":
                            if config.ENABLE_LOG:
                                print("请输入内容：")

        except asyncio.CancelledError:
            if config.ENABLE_LOG:
                print("接收任务已取消")
        except Exception as e:
            if config.ENABLE_LOG:
                print(f"接收消息错误: {e}")
        finally:
            self.stop()
            self.is_session_finished = True

    async def process_audio_file(self) -> None:
        await self.process_audio_file_input(self.audio_file_path)

    async def process_text_input(self) -> None:
        await self.client.say_hello()
        await self.say_hello_over_event.wait()

        """主逻辑：处理文本输入和WebSocket通信"""
        # 确保连接最终关闭
        try:
            # 启动输入监听线程
            input_queue = queue.Queue()
            input_thread = threading.Thread(target=self.input_listener, args=(input_queue,), daemon=True)
            input_thread.start()
            # 主循环：处理输入和上下文结束
            while self.is_running:
                try:
                    # 检查是否有输入（非阻塞）
                    input_str = input_queue.get_nowait()
                    if input_str is None:
                        # 输入流关闭
                        if config.ENABLE_LOG:
                            print("Input channel closed")
                        break
                    if input_str:
                        # 发送输入内容
                        await self.client.chat_text_query(input_str)
                except queue.Empty:
                    # 无输入时短暂休眠
                    await asyncio.sleep(0.1)
                except Exception as e:
                    if config.ENABLE_LOG:
                        print(f"Main loop error: {e}")
                    break
        finally:
            if config.ENABLE_LOG:
                print("exit text input")

    def input_listener(self, input_queue: queue.Queue) -> None:
        """在单独线程中监听标准输入"""
        if config.ENABLE_LOG:
            print("Start listening for input")
        try:
            while True:
                # 读取标准输入（阻塞操作）
                line = sys.stdin.readline()
                if not line:
                    # 输入流关闭
                    input_queue.put(None)
                    break
                input_str = line.strip()
                input_queue.put(input_str)
        except Exception as e:
            if config.ENABLE_LOG:
                print(f"Input listener error: {e}")
            input_queue.put(None)

    async def process_audio_file_input(self, audio_file_path: str) -> None:
        timer.start("process_audio_file")
        # 读取WAV文件
        with wave.open(audio_file_path, 'rb') as wf:
            chunk_size = config.input_audio_config["chunk"]
            framerate = wf.getframerate()  # 采样率（如16000Hz）
            # 时长 = chunkSize（帧数） ÷ 采样率（帧/秒）
            sleep_seconds = chunk_size / framerate
            if config.ENABLE_LOG:
                print(f"开始处理音频文件: {audio_file_path}")

            # 分块读取并发送音频数据
            while True:
                audio_data = wf.readframes(chunk_size)
                if not audio_data:
                    break  # 文件读取完毕

                await self.client.task_request(audio_data)
                # sleep与chunk对应的音频时长一致，模拟实时输入
                await asyncio.sleep(sleep_seconds)

            if config.ENABLE_LOG:
                print(f"音频文件处理完成，等待服务器响应...")
        timer.end("process_audio_file")

    async def process_silence_audio(self) -> None:
        """发送静音音频"""
        silence_data = b'\x00' * 320
        await self.client.task_request(silence_data)

    async def process_microphone_input(self) -> None:
        timer.start("process_microphone")
        await self.client.say_hello()
        await self.say_hello_over_event.wait()
        await self.client.chat_text_query("你好，我也叫豆包")

        """处理麦克风输入"""
        stream = self.audio_device.open_input_stream()
        if config.ENABLE_LOG:
            print("已打开麦克风，请讲话...")

        while self.is_recording:
            try:
                # 添加exception_on_overflow=False参数来忽略溢出错误
                audio_data = stream.read(config.input_audio_config["chunk"], exception_on_overflow=False)
                save_input_pcm_to_wav(audio_data, "input.pcm")
                await self.client.task_request(audio_data)
                await asyncio.sleep(0.01)  # 避免CPU过度使用
            except Exception as e:
                if config.ENABLE_LOG:
                    print(f"读取麦克风数据出错: {e}")
                await asyncio.sleep(0.1)  # 给系统一些恢复时间
        timer.end("process_microphone")

    async def start(self) -> None:
        """启动对话会话"""
        timer.start("session_start")
        try:
            await self.client.connect()

            if self.mod == "text":
                asyncio.create_task(self.process_text_input())
                asyncio.create_task(self.receive_loop())
                while self.is_running:
                    await asyncio.sleep(0.1)
            else:
                if self.is_audio_file_input:
                    asyncio.create_task(self.process_audio_file())
                    await self.receive_loop()
                else:
                    asyncio.create_task(self.process_microphone_input())
                    asyncio.create_task(self.receive_loop())
                    while self.is_running:
                        await asyncio.sleep(0.1)

            await self.client.finish_session()
            while not self.is_session_finished:
                await asyncio.sleep(0.1)
            await self.client.finish_connection()
            await asyncio.sleep(0.1)
            await self.client.close()
            if config.ENABLE_LOG:
                print(f"dialog request logid: {self.client.logid}, chat mod: {self.mod}")
            save_output_to_file(self.audio_buffer, "output.pcm")

            # 会话结束后，尝试把本次对话写入 Viking 记忆库
            if self.memory_client is not None and self.conversation_messages:
                try:
                    await self.memory_client.add_session(self.session_id, self.conversation_messages)
                    if config.ENABLE_LOG:
                        print("memory archived")
                except Exception as e:
                    if config.ENABLE_LOG:
                        print(f"memory archive failed: {e}")
        except Exception as e:
            if config.ENABLE_LOG:
                print(f"会话错误: {e}")
        finally:
            if not self.is_audio_file_input:
                self.audio_device.cleanup()
            timer.end("session_start")
            # 打印计时摘要
            timer.print_summary()


def save_input_pcm_to_wav(pcm_data: bytes, filename: str) -> None:
    """保存PCM数据为WAV文件"""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(config.input_audio_config["channels"])
        wf.setsampwidth(2)  # paInt16 = 2 bytes
        wf.setframerate(config.input_audio_config["sample_rate"])
        wf.writeframes(pcm_data)


def save_output_to_file(audio_data: bytes, filename: str) -> None:
    """保存原始PCM音频数据到文件"""
    if not audio_data:
        if config.ENABLE_LOG:
            print("No audio data to save.")
        return
    try:
        with open(filename, 'wb') as f:
            f.write(audio_data)
    except IOError as e:
        if config.ENABLE_LOG:
            print(f"Failed to save pcm file: {e}")
