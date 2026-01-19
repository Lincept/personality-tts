"""
文本清理工具 - 移除 Markdown 格式和特殊符号
用于 TTS 前的文本预处理
"""
import re


class TextCleaner:
    """文本清理器"""

    @staticmethod
    def clean_for_tts(text: str) -> str:
        """
        清理文本，移除不适合 TTS 的符号

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        if not text:
            return text

        # 移除 Markdown 标题符号
        text = re.sub(r'#{1,6}\s+', '', text)

        # 移除 Markdown 粗体/斜体
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **粗体**
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *斜体*
        text = re.sub(r'__([^_]+)__', r'\1', text)      # __粗体__
        text = re.sub(r'_([^_]+)_', r'\1', text)        # _斜体_

        # 移除 Markdown 列表符号
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # - 列表
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # 1. 列表

        # 移除 Markdown 分隔线
        text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)

        # 移除 Markdown 代码块
        text = re.sub(r'```[^`]*```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 移除 Markdown 链接
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # 移除表情符号（可选，根据需要）
        # text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+', '', text)

        # 移除多余的空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    @staticmethod
    def should_send_to_tts(text: str) -> bool:
        """
        判断文本是否应该发送到 TTS

        Args:
            text: 文本

        Returns:
            是否应该发送
        """
        if not text or not text.strip():
            return False

        # 如果只包含符号，不发送
        if re.match(r'^[\s\-*#_`]+$', text):
            return False

        # 如果只包含空白，不发送
        if not text.strip():
            return False

        return True

    @staticmethod
    def clean_chunk(chunk: str) -> str:
        """
        清理单个文本块（用于流式处理）

        Args:
            chunk: 文本块

        Returns:
            清理后的文本块
        """
        # 移除常见的 Markdown 符号
        chunk = chunk.replace('**', '')
        chunk = chunk.replace('__', '')
        chunk = chunk.replace('###', '')
        chunk = chunk.replace('---', '')

        # 移除列表符号（但保留内容）
        chunk = re.sub(r'^\s*[-*+]\s+', '', chunk)
        chunk = re.sub(r'^\s*\d+\.\s+', '', chunk)

        return chunk
