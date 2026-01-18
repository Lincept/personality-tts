"""del_agent.memory - 记忆层框架

从 src/memory 迁移而来，用于支持词典管理等功能。

包含：
- store.py: 记忆存储抽象接口
- mem0_manager.py: Mem0 实现
- factory.py: 工厂方法
"""

from .store import MemoryStore, MemoryRecord, NullMemoryStore
from .mem0_manager import Mem0Manager
from .factory import create_memory_store

__all__ = [
    "MemoryStore",
    "MemoryRecord",
    "NullMemoryStore",
    "Mem0Manager",
    "create_memory_store",
]
