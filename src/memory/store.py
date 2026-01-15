"""src.memory.store

为“长期记忆”抽象统一接口，便于替换/适配不同记忆框架（mem0、langchain、chroma、自研等）。

设计目标：
- 业务层（MemoryEnhancedChat / VoiceAssistantPrompt / tools）只依赖 MemoryStore。
- 后端实现（Mem0Manager 等）负责具体 SDK 调用与持久化细节。
- 保留老代码的 if memory_manager and memory_manager.enabled 判断语义。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class MemoryRecord:
    """一次检索命中的记忆记录（最小通用结构）"""

    content: str
    id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryStore(Protocol):
    """长期记忆后端接口。

    约定：
    - enabled=False 时，所有方法都应安全返回（不抛异常）。
    - __bool__ 语义与 enabled 保持一致，方便兼容旧代码。
    """

    enabled: bool

    def __bool__(self) -> bool: ...

    @property
    def supports_relationships(self) -> bool:
        """是否支持 relationship 类记忆（如 Neo4j 图谱）。"""
        ...

    def search(self, query: str, user_id: str, limit: int = 5) -> List[MemoryRecord]:
        """返回结构化结果，便于业务层按需格式化。"""
        ...

    def save(
        self,
        memory: str,
        user_id: str,
        *,
        kind: str = "fact",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """保存一条记忆。

        kind 建议值：fact / relationship / other
        """
        ...

    def add_conversation(self, user_input: str, assistant_response: str, user_id: str) -> None:
        """保存一轮对话（以对话消息形式）。"""
        ...

    def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """获取所有记忆（后端原始结构即可）。"""
        ...

    def clear(self, user_id: str) -> None:
        """清空用户记忆。"""
        ...

    def close(self) -> None:
        """关闭/flush 资源，尽量保证落盘。"""
        ...


class NullMemoryStore:
    """空实现：用于在未启用记忆时保持调用方逻辑简单。"""

    enabled = False

    def __bool__(self) -> bool:
        return False

    @property
    def supports_relationships(self) -> bool:
        return False

    def search(self, query: str, user_id: str, limit: int = 5) -> List[MemoryRecord]:
        return []

    def save(
        self,
        memory: str,
        user_id: str,
        *,
        kind: str = "fact",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        return None

    def add_conversation(self, user_input: str, assistant_response: str, user_id: str) -> None:
        return None

    def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        return []

    def clear(self, user_id: str) -> None:
        return None

    def close(self) -> None:
        return None
