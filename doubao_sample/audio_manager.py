import asyncio
import threading
import queue
import time
import random
import signal
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass
import wave
import pyaudio

from realtime_dialog_client import RealtimeDialogClient
import config
from timer import timer


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

    def terminate(self) -> None:
        """清理音频设备资源"""
        for stream in [self.input_stream, self.output_stream]:
            if stream:
                stream.stop_stream()
                stream.close()
        self.pyaudio.terminate()


class AudioManager:
    """音频管理器，专注于语音实时输入输出性能监控"""
    
    def __init__(self, audio_file_path: Optional[str] = None, recv_timeout: int = 30):
        self.audio_file_path = audio_file_path
        self.is_audio_file_input = audio_file_path is not None
        self.recv_timeout = recv_timeout
        self.client = None
        self.audio_device = None
        self.audio_queue = None
        self.output_stream = None
        self.is_recording = False
        self.is_playing = False
        self.is_running = True
        self.is_session_finished = False
        self.player_thread = None
        self.audio_buffer = b''
        self.is_user_querying = False
        self.is_sending_chat_tts_text = False
        self.say_hello_over_event = threading.Event()

    def stop(self):
        """停止所有音频操作"""
        self.is_recording = False
        self.is_playing = False
        self.is_running = False
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        if self.audio_device:
            self.audio_device.terminate()

    def _keyboard_signal(self, signum, frame):
        """处理键盘中断信号"""
        if config.ENABLE_LOG:
            print("\n检测到中断信号，正在优雅退出...")
        self.stop()
        self.is_session_finished = True

    def handle_server_response(self, response: Dict[str, Any]) -> None:
        """处理服务器响应"""
        if response == {}:
            return
            
        if response['message_type'] == 'SERVER_ACK' and isinstance(response.get('payload_msg'), bytes):
            audio_data = response['payload_msg']
            
            # 记录音频数据接收
            timer.record_audio_data("audio_receive", len(audio_data))
            
            if self.is_sending_chat_tts_text:
                return
                
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

            if event == 350 and payload_msg.get("tts_type") in ["chat_tts_text"]:
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

    async def trigger_chat_rag_text(self):
        """概率触发发送ChatRAGText请求"""
        if config.ENABLE_LOG:
            print("hit ChatRAGText event, start sending...")
        await self.client.chat_rag_text(
            is_user_querying=self.is_user_querying,
            start=True,
            end=False,
            content="emmm",
        )

    def _audio_player_thread(self):
        """音频播放线程"""
        while self.is_playing:
            try:
                audio_data = self.audio_queue.get(timeout=1.0)
                if audio_data is not None:
                    # 记录音频播放开始
                    timer.start("audio_play_single", "audio_play")
                    self.output_stream.write(audio_data)
                    # 记录音频播放结束
                    timer.end("audio_play_single", "audio_play")
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                if config.ENABLE_LOG:
                    print(f"音频播放错误: {e}")
                time.sleep(0.1)

    async def start(self) -> None:
        """启动对话会话"""
        timer.start("session_start")
        try:
            self.client = RealtimeDialogClient(recv_timeout=self.recv_timeout, mod="audio_file" if self.is_audio_file_input else "mic")
            await self.client.connect()
            
            self.audio_queue = queue.Queue()
            if not self.is_audio_file_input:
                self.audio_device = AudioDeviceManager(
                    AudioConfig(**config.input_audio_config),
                    AudioConfig(**config.output_audio_config)
                )
                self.output_stream = self.audio_device.open_output_stream()
                self.is_recording = True
                self.is_playing = True
                self.player_thread = threading.Thread(target=self._audio_player_thread)
                self.player_thread.daemon = True
                self.player_thread.start()

            signal.signal(signal.SIGINT, self._keyboard_signal)
            
            # 根据输入模式启动相应的处理流程
            if self.is_audio_file_input:
                await self.process_audio_file()
            else:
                await self.process_microphone_input()
                
            # 等待会话结束
            while not self.is_session_finished:
                await asyncio.sleep(1)
                
        finally:
            self.stop()
            timer.end("session_start")
            # 打印完整的性能摘要
            timer.print_summary()

    async def process_text_input(self) -> None:
        """处理文本输入"""
        await self.client.say_hello()
        await self.say_hello_over_event.wait()
        
        try:
            input_queue = queue.Queue()
            input_thread = threading.Thread(target=self.input_listener, args=(input_queue,), daemon=True)
            input_thread.start()
            
            while self.is_running:
                try:
                    input_str = input_queue.get_nowait()
                    if input_str is None:
                        break
                    if input_str:
                        await self.client.chat_text_query(input_str)
                except queue.Empty:
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
                line = sys.stdin.readline()
                if not line:
                    input_queue.put(None)
                    break
                input_str = line.strip()
                input_queue.put(input_str)
        except Exception as e:
            if config.ENABLE_LOG:
                print(f"Input listener error: {e}")
            input_queue.put(None)

    async def process_audio_file_input(self, audio_file_path: str) -> None:
        """处理音频文件输入"""
        timer.start("audio_file_processing")
        
        # 记录音频文件处理开始
        timer.start("audio_file_read")
        
        with wave.open(audio_file_path, 'rb') as wf:
            chunk_size = config.input_audio_config["chunk"]
            framerate = wf.getframerate()
            sleep_seconds = chunk_size / framerate
            
            if config.ENABLE_LOG:
                print(f"开始处理音频文件: {audio_file_path}")
                print(f"采样率: {framerate}Hz, 分块大小: {chunk_size}, 延迟时间: {sleep_seconds:.4f}s")

            chunk_count = 0
            total_audio_size = 0
            
            while True:
                audio_data = wf.readframes(chunk_size)
                if not audio_data:
                    break
                    
                chunk_count += 1
                total_audio_size += len(audio_data)
                
                # 记录单个音频块的发送时间
                timer.start(f"audio_send_chunk_{chunk_count}", "audio_send")
                
                await self.client.task_request(audio_data)
                
                # 记录音频数据发送
                timer.record_audio_data("audio_send", len(audio_data))
                
                # 结束当前块的发送计时
                timer.end(f"audio_send_chunk_{chunk_count}", "audio_send")
                
                # 模拟实时输入的延迟
                await asyncio.sleep(sleep_seconds)

            timer.end("audio_file_read")
            
            if config.ENABLE_LOG:
                print(f"音频文件处理完成，共 {chunk_count} 个数据块，总大小: {total_audio_size} bytes")
                
        timer.end("audio_file_processing")

    async def process_silence_audio(self) -> None:
        """发送静音音频"""
        silence_data = b'\x00' * 320
        await self.client.task_request(silence_data)

    async def process_microphone_input(self) -> None:
        """处理麦克风输入"""
        await self.client.say_hello()
        await self.say_hello_over_event.wait()
        await self.client.chat_text_query("你好，我也叫豆包")

        stream = self.audio_device.open_input_stream()
        if config.ENABLE_LOG:
            print("已打开麦克风，请讲话...")

        audio_chunk_count = 0
        
        while self.is_recording:
            try:
                audio_data = stream.read(config.input_audio_config["chunk"], exception_on_overflow=False)
                audio_chunk_count += 1
                
                # 记录麦克风音频输入
                timer.record_audio_data("microphone_input", len(audio_data))
                
                # 记录单个音频块的发送时间
                timer.start(f"mic_send_chunk_{audio_chunk_count}", "microphone_send")
                
                await self.client.task_request(audio_data)
                
                # 结束当前块的发送计时
                timer.end(f"mic_send_chunk_{audio_chunk_count}", "microphone_send")
                
                await asyncio.sleep(0.01)
                
            except Exception as e:
                if config.ENABLE_LOG:
                    print(f"读取麦克风数据出错: {e}")
                await asyncio.sleep(0.1)