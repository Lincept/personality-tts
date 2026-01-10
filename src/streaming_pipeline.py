"""
流式处理管道 - LLM 流式输出 → TTS 流式合成 → 音频流式播放
"""
import queue
import threading
import re
from typing import Generator, Callable
import time


class StreamingPipeline:
    def __init__(self):
        """初始化流式处理管道"""
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()

    def sentence_splitter(self, text_stream: Generator[str, None, None]) -> Generator[str, None, None]:
        """
        将流式文本按句子分割

        Args:
            text_stream: LLM 流式输出的文本生成器

        Yields:
            完整的句子
        """
        buffer = ""
        # 句子结束标记
        sentence_endings = r'[。！？\n.!?]'

        for chunk in text_stream:
            buffer += chunk

            # 检查是否有完整的句子
            while True:
                match = re.search(sentence_endings, buffer)
                if match:
                    # 找到句子结束符
                    end_pos = match.end()
                    sentence = buffer[:end_pos].strip()

                    if sentence:
                        yield sentence

                    buffer = buffer[end_pos:]
                else:
                    break

        # 处理剩余的文本
        if buffer.strip():
            yield buffer.strip()

    def text_producer(self, text_stream: Generator[str, None, None],
                     on_sentence: Callable[[str], None] = None):
        """
        文本生产者：从 LLM 流式输出中提取句子

        Args:
            text_stream: LLM 流式输出
            on_sentence: 每个句子的回调函数
        """
        try:
            for sentence in self.sentence_splitter(text_stream):
                if self.stop_event.is_set():
                    break

                self.text_queue.put(sentence)

                if on_sentence:
                    on_sentence(sentence)

        except Exception as e:
            print(f"\n[文本生产者错误]: {e}")
        finally:
            self.text_queue.put(None)  # 结束信号

    def tts_processor(self, tts_client, output_dir: str):
        """
        TTS 处理器：将句子转换为音频

        Args:
            tts_client: TTS 客户端
            output_dir: 音频输出目录
        """
        import os
        from datetime import datetime

        sentence_count = 0

        try:
            while not self.stop_event.is_set():
                try:
                    sentence = self.text_queue.get(timeout=1)

                    if sentence is None:  # 结束信号
                        break

                    # 生成音频文件名
                    sentence_count += 1
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    audio_filename = f"stream_{timestamp}_{sentence_count}.wav"
                    audio_path = os.path.join(output_dir, audio_filename)

                    # 调用 TTS
                    result = tts_client.synthesize(sentence, audio_path)

                    if result.get("success"):
                        self.audio_queue.put(audio_path)
                    else:
                        print(f"\n[TTS 错误]: {result.get('error')}")

                except queue.Empty:
                    continue

        except Exception as e:
            print(f"\n[TTS 处理器错误]: {e}")
        finally:
            self.audio_queue.put(None)  # 结束信号

    def audio_player(self, player):
        """
        音频播放器：流式播放生成的音频

        Args:
            player: AudioPlayer 实例
        """
        try:
            while not self.stop_event.is_set():
                try:
                    audio_path = self.audio_queue.get(timeout=1)

                    if audio_path is None:  # 结束信号
                        break

                    # 播放音频（阻塞）
                    player.play(audio_path, blocking=True)

                except queue.Empty:
                    continue

        except Exception as e:
            print(f"\n[音频播放器错误]: {e}")

    def run(self, text_stream: Generator[str, None, None],
            tts_client, audio_player, output_dir: str,
            on_sentence: Callable[[str], None] = None):
        """
        运行完整的流式处理管道

        Args:
            text_stream: LLM 流式输出
            tts_client: TTS 客户端
            audio_player: 音频播放器
            output_dir: 音频输出目录
            on_sentence: 每个句子的回调函数
        """
        # 重置状态
        self.stop_event.clear()

        # 启动三个线程
        text_thread = threading.Thread(
            target=self.text_producer,
            args=(text_stream, on_sentence),
            daemon=True
        )

        tts_thread = threading.Thread(
            target=self.tts_processor,
            args=(tts_client, output_dir),
            daemon=True
        )

        player_thread = threading.Thread(
            target=self.audio_player,
            args=(audio_player,),
            daemon=True
        )

        # 启动所有线程
        text_thread.start()
        tts_thread.start()
        player_thread.start()

        # 等待所有线程完成
        text_thread.join()
        tts_thread.join()
        player_thread.join()

    def stop(self):
        """停止流式处理"""
        self.stop_event.set()


class BufferedSentenceSplitter:
    """
    带缓冲的句子分割器
    更智能地处理中英文混合、标点符号等
    """
    def __init__(self, min_length: int = 5, max_length: int = 50):
        """
        Args:
            min_length: 最小句子长度（避免过短的句子）
            max_length: 最大句子长度（避免过长的句子）
        """
        self.min_length = min_length
        self.max_length = max_length
        self.buffer = ""

    def add_chunk(self, chunk: str) -> list:
        """
        添加文本块，返回完整的句子列表

        Args:
            chunk: 文本块

        Returns:
            完整句子列表
        """
        self.buffer += chunk
        sentences = []

        # 句子结束标记（按优先级）
        strong_endings = r'[。！？\n]'  # 强结束符
        weak_endings = r'[.!?]'        # 弱结束符（英文）

        while len(self.buffer) > 0:
            # 如果缓冲区太长，强制分割
            if len(self.buffer) > self.max_length:
                # 尝试在标点处分割
                match = re.search(r'[，,、；;]', self.buffer)
                if match:
                    pos = match.end()
                    sentence = self.buffer[:pos].strip()
                    if sentence:
                        sentences.append(sentence)
                    self.buffer = self.buffer[pos:]
                    continue
                else:
                    # 没有标点，强制分割
                    sentence = self.buffer[:self.max_length].strip()
                    if sentence:
                        sentences.append(sentence)
                    self.buffer = self.buffer[self.max_length:]
                    continue

            # 查找强结束符
            match = re.search(strong_endings, self.buffer)
            if match:
                end_pos = match.end()
                sentence = self.buffer[:end_pos].strip()

                if len(sentence) >= self.min_length:
                    sentences.append(sentence)
                    self.buffer = self.buffer[end_pos:]
                    continue
                elif len(sentence) > 0:
                    # 句子太短，继续累积
                    break

            # 查找逗号等中等停顿符（新增）
            if len(self.buffer) >= self.min_length:
                match = re.search(r'[，,]', self.buffer)
                if match:
                    end_pos = match.end()
                    sentence = self.buffer[:end_pos].strip()

                    if len(sentence) >= self.min_length:
                        sentences.append(sentence)
                        self.buffer = self.buffer[end_pos:]
                        continue

            # 查找弱结束符（仅当缓冲区足够长时）
            if len(self.buffer) >= self.min_length * 2:
                match = re.search(weak_endings, self.buffer)
                if match:
                    end_pos = match.end()
                    sentence = self.buffer[:end_pos].strip()

                    if len(sentence) >= self.min_length:
                        sentences.append(sentence)
                        self.buffer = self.buffer[end_pos:]
                        continue

            # 没有找到合适的分割点，等待更多文本
            break

        return sentences

    def flush(self) -> list:
        """
        刷新缓冲区，返回剩余的文本

        Returns:
            剩余文本列表
        """
        sentences = []
        if self.buffer.strip():
            sentences.append(self.buffer.strip())
        self.buffer = ""
        return sentences
