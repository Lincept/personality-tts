import asyncio
import queue
import signal
import sys
import threading
import time
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import pyaudio

import config
from realtime_dialog_client import RealtimeDialogClient
from VikingMemory import VikingMemory, build_external_rag_payload
from utils import timer, normalize_messages, save_input_pcm_to_wav, save_output_to_file


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
                 mod: str = "audio", recv_timeout: int = 10, use_memory: bool = False, use_aec: bool = False):
        self.use_memory = use_memory
        self.use_aec = use_aec
        self.aec_processor = None
        if self.use_memory:
            self.memory_client = VikingMemory()
            self.current_input = ""
            self.message_pairs = {}
            self.memory_injected = False
        self.audio_file_path = audio_file_path
        self.recv_timeout = recv_timeout
        self.is_audio_file_input = self.audio_file_path != ""
        if self.is_audio_file_input:
            mod = 'audio_file'
        else:
            self.say_hello_over_event = asyncio.Event()
        self.mod = mod

        self.session_id = str(uuid.uuid4())
        self.fallback_message_id = f"session:{self.session_id}"
        self.client = RealtimeDialogClient(config=ws_config, session_id=self.session_id,
                                           output_audio_format=output_audio_format, mod=mod, recv_timeout=recv_timeout)
        if output_audio_format == "pcm_s16le":
            config.output_audio_config["format"] = "pcm_s16le"
            config.output_audio_config["bit_size"] = pyaudio.paInt16

        self.is_running = True
        self.is_session_finished = False
        self.is_user_querying = False
        self.is_sending_tts_or_rag = False
        self.audio_buffer = b''

        signal.signal(signal.SIGINT, self._keyboard_signal)
        self.audio_queue = queue.Queue()
        if not self.is_audio_file_input:
            self.audio_device = AudioDeviceManager(
                AudioConfig(**config.input_audio_config),
                AudioConfig(**config.output_audio_config)
            )
            # 初始化音频队列和输出流
            self.output_stream = self.audio_device.open_output_stream()
            
            # 初始化 AEC 处理器（如果启用）
            if self.use_aec:
                try:
                    from aec.aec_processor import WebRTCAECProcessor
                    self.aec_processor = WebRTCAECProcessor(
                        sample_rate=config.input_audio_config["sample_rate"]
                    )
                    if config.ENABLE_LOG:
                        print("✅ AEC 处理器已初始化")
                except Exception as e:
                    if config.ENABLE_LOG:
                        print(f"⚠️ AEC 初始化失败: {e}")
                    self.aec_processor = None
            
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
                    # 如果启用 AEC，将播放的音频作为参考信号
                    if self.use_aec and self.aec_processor:
                        try:
                            import numpy as np
                            
                            # 根据输出音频格式转换数据
                            output_format = config.output_audio_config["bit_size"]
                            output_sample_rate = config.output_audio_config["sample_rate"]
                            input_sample_rate = config.input_audio_config["sample_rate"]
                            
                            if output_format == pyaudio.paFloat32:
                                # float32 格式：范围 [-1.0, 1.0]
                                audio_array = np.frombuffer(audio_data, dtype=np.float32)
                                # 转换为 int16：范围 [-32768, 32767]，需要 clip 防止溢出
                                audio_array = np.clip(audio_array * 32768.0, -32768, 32767).astype(np.int16)
                            elif output_format == pyaudio.paInt16:
                                # int16 格式：直接使用
                                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                            else:
                                raise ValueError(f"不支持的音频格式: {output_format}")
                            
                            # 如果采样率不匹配，需要重采样
                            if output_sample_rate != input_sample_rate:
                                # 简单的降采样：每隔 n 个样本取一个
                                # 24000 -> 16000: 取样比例 = 16000/24000 = 2/3
                                downsample_ratio = input_sample_rate / output_sample_rate
                                indices = np.arange(0, len(audio_array), 1/downsample_ratio).astype(int)
                                audio_array = audio_array[indices[:int(len(audio_array) * downsample_ratio)]]
                            
                            self.aec_processor.add_reference(audio_array)
                        except Exception as e:
                            if config.ENABLE_LOG:
                                print(f"⚠️ AEC 参考信号添加失败: {e}")
                    
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
        if response['message_type'] == 'SERVER_ACK' and isinstance(response.get('payload_msg'), bytes) and not self.is_sending_tts_or_rag:
            if config.ENABLE_LOG:
                print(f"\n接收到音频数据: {len(response['payload_msg'])} 字节")
            audio_data = response['payload_msg']
            if not self.is_audio_file_input:
                self.audio_queue.put(audio_data)
            self.audio_buffer += audio_data
        elif response['message_type'] == 'SERVER_FULL_RESPONSE':
            if config.ENABLE_LOG:
                print(f"服务器响应: {response}")
            event = response.get('event')
            payload_msg = response.get('payload_msg', {})

            if event == 450:
                if config.ENABLE_LOG:
                    print(f"清空缓存音频: {response['session_id']}")
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
                        if reply_id:
                            self.message_pairs[reply_id] = {
                                "user": self.current_input,
                                "assistant": ""
                            }

            if event == 451 and self.use_memory:
                results = payload_msg.get("results", [])
                extra = payload_msg.get("extra")
                if "endpoint" not in extra or bool(extra["endpoint"]) != True:
                    return
                # 用户说完话了，默认加入RAG，且不接收default音频
                self.current_input = results[0]["text"]
                print(f"current inputcurrent input: {self.current_input}")
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
                if content and reply_id in self.message_pairs:
                    self.message_pairs[reply_id]["assistant"] += content
                

        elif response['message_type'] == 'SERVER_ERROR':
            if config.ENABLE_LOG:
                print(f"服务器错误: {response['payload_msg']}")
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

    # async def trigger_chat_rag_text(self):
    #     await asyncio.sleep(0) # 模拟查询外部RAG的耗时，这里为了不影响GTA安抚话术的播报，直接sleep 5秒
    #     if config.ENABLE_LOG:
    #         print("hit ChatRAGText event, start sending...")
    #     await self.client.chat_rag_text(self.is_user_querying, external_rag='[{"title":"北京天气","content":"今天北京整体以晴到多云为主，但西部和北部地带可能会出现分散性雷阵雨，特别是午后至傍晚时段需注意突发降雨。\n💨 风况与湿度\n风力较弱，一般为 2–3 级南风或西南风\n白天湿度较高，早晚略凉爽"}]')

    async def inject_memory_once(self) -> None:
        if not self.use_memory or self.memory_injected:
            return
        try:
            profile = await self.memory_client.search_profile()
            recent_events = await self.memory_client.search_recent_events(1, 2)
            memory_summary = (
                "已知用户画像与近期事件（仅用于对话参考）：\n"
                f"Profile: {profile}\n"
                f"RecentEvents: {recent_events}"
            )
            items = [
                {"role": "user", "text": "记忆摘要"},
                {"role": "assistant", "text": memory_summary},
            ]
            await self.client.conversation_create(items)
            self.memory_injected = True
        except Exception as e:
            if config.ENABLE_LOG:
                print(f"memory inject error: {e}")

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
                                print(f"SayHello over, input loop start...")
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
                        if self.use_memory:
                            self.current_input = input_str
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

    def _keyboard_signal(self, sig, frame):
        if config.ENABLE_LOG:
            print(f"receive keyboard Ctrl+C")
        self.stop()

    async def process_microphone_input(self) -> None:
        timer.start("process_microphone")
        await self.client.say_hello()
        await self.say_hello_over_event.wait()

        """处理麦克风输入"""
        stream = self.audio_device.open_input_stream()
        if config.ENABLE_LOG:
            print("已打开麦克风，请讲话...")

        while self.is_recording:
            try:
                # 添加exception_on_overflow=False参数来忽略溢出错误
                audio_data = stream.read(config.input_audio_config["chunk"], exception_on_overflow=False)
                
                # 如果启用 AEC，对麦克风输入进行处理
                if self.use_aec and self.aec_processor:
                    try:
                        import numpy as np
                        # 将音频数据转换为 numpy 数组（输入是 int16 格式）
                        input_format = config.input_audio_config["bit_size"]
                        if input_format == pyaudio.paInt16:
                            audio_array = np.frombuffer(audio_data, dtype=np.int16)
                            # 应用 AEC 处理
                            processed_array = self.aec_processor.process(audio_array)
                            # 转换回 bytes
                            audio_data = processed_array.tobytes()
                        else:
                            if config.ENABLE_LOG:
                                print(f"⚠️ AEC 仅支持 int16 输入格式，当前格式: {input_format}")
                    except Exception as e:
                        if config.ENABLE_LOG:
                            print(f"⚠️ AEC 处理失败，使用原始音频: {e}")
                
                data_dir = Path(__file__).resolve().parent / "data"
                data_dir.mkdir(parents=True, exist_ok=True)
                save_input_pcm_to_wav(audio_data, str(data_dir / "input.pcm"))
                await self.client.task_request(audio_data)
                await asyncio.sleep(0.01)  # 避免CPU过度使用
            except Exception as e:
                if config.ENABLE_LOG:
                    print(f"读取麦克风数据出错: {e}")
                await asyncio.sleep(0.1)  # 给系统一些恢复时间
        timer.end("process_microphone")

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

    async def start(self) -> None:
        """启动对话会话"""
        timer.start("session_start")
        try:
            await self.client.connect()

            if self.use_memory:
                await self.inject_memory_once()

            if self.mod == "text":
                asyncio.create_task(self.process_text_input())
                asyncio.create_task(self.receive_loop())
                while self.is_running:
                    await asyncio.sleep(0.1)
            else:
                if self.is_audio_file_input:
                    asyncio.create_task(self.process_audio_file_input(self.audio_file_path))
                    await self.receive_loop()
                else:
                    asyncio.create_task(self.process_microphone_input())
                    asyncio.create_task(self.receive_loop())
                    while self.is_running:
                        await asyncio.sleep(0.1)

            if self.use_memory:
                # import pprint
                # print()
                # pprint.pprint(self.message_pairs, indent=4)
                # print()
                nms = normalize_messages(self.message_pairs)
                if config.ENABLE_LOG:
                    print(f"Upload Messages for memory length: {len(nms)}")
                    print(f"Upload Message Contents: {nms}")
                await self.memory_client.save_memory(self.session_id, messages=nms)

            await self.client.finish_session()
            while not self.is_session_finished:
                await asyncio.sleep(0.1)
            await self.client.finish_connection()
            await asyncio.sleep(0.1)
            await self.client.close()
            if config.ENABLE_LOG:
                print(f"dialog request logid: {self.client.logid}, chat mod: {self.mod}")
            data_dir = Path(__file__).resolve().parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            save_output_to_file(self.audio_buffer, str(data_dir / "output.pcm"))
        except Exception as e:
            if config.ENABLE_LOG:
                print(f"会话错误: {e}")
            self.stop()
            await asyncio.sleep(1)
            sys.exit(1)
        finally:
            if not self.is_audio_file_input:
                self.audio_device.cleanup()
            timer.end("session_start")
            # 打印计时摘要
            timer.print_summary()

    def stop(self):
        self.is_recording = False
        self.is_playing = False
        self.is_running = False