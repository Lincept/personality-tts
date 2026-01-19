"""
Memory 模块 - Mem0 记忆管理

包含两种记忆管理方案：
1. memory_tools - 基于 Function Calling 的工具化方案（旧）
2. memory_chat - 基于结构化输出的两阶段方案（新，推荐）
"""

from .store import MemoryStore, NullMemoryStore, MemoryRecord
from .factory import create_memory_store
from .mem0_manager import Mem0Manager
from .memory_tools import (
    initialize_memory_tools,
    save_memories,
    search_memories,
    get_tool_definitions,
    execute_tool
)
from .tools import MemoryTools
from .memory_chat import (
    MemoryEnhancedChat,
    create_memory_chat,
    AnalysisResult,
    FinalResponse,
    MemoryItem
)

__all__ = [
    # 抽象接口（推荐）
    'MemoryStore',
    'NullMemoryStore',
    'MemoryRecord',
    'create_memory_store',
    # Mem0 管理器
    'Mem0Manager',
    # 工具层（推荐）
    'MemoryTools',
    # 旧方案：Function Calling
    'initialize_memory_tools',
    'save_memories',
    'search_memories',
    'get_tool_definitions',
    'execute_tool',
    # 新方案：结构化输出（推荐）
    'MemoryEnhancedChat',
    'create_memory_chat',
    'AnalysisResult',
    'FinalResponse',
    'MemoryItem'
]
