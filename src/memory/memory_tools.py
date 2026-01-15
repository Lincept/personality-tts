"""Deprecated: 旧版工具化记忆管理（兼容层）。

历史上该模块直接依赖 Mem0Manager，并且与 mem0_tools.py 存在大量重复。
现在统一由 src.memory.tools.MemoryTools 实现，方便未来替换不同记忆框架。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .store import MemoryStore, NullMemoryStore
from .tools import MemoryTools


# 全局变量（为兼容旧调用方式保留）
_tools: Optional[MemoryTools] = None


def initialize_memory_tools(mem0_manager, user_id: str = "default_user", verbose: bool = False):
    """
    初始化记忆工具（类似 mem0 案例）

    Args:
        mem0_manager: Mem0Manager 实例
        user_id: 用户 ID
        verbose: 是否显示详细日志（默认 False）
    """
    global _tools
    memory_store: MemoryStore = mem0_manager if mem0_manager is not None else NullMemoryStore()
    _tools = MemoryTools(memory_store=memory_store, user_id=user_id, verbose=verbose)


def save_memories(memory: str) -> str:
    """
    保存用户记忆到长期记忆库（向量存储）

    当用户分享事实性信息时使用此工具：
    - 个人偏好（喜欢/不喜欢的事物）
    - 个人信息（姓名、职业、爱好等）
    - 重要事实和上下文

    不要保存简单的问候或临时信息。

    Args:
        memory: 要保存的记忆内容

    Returns:
        确认消息
    """
    if not _tools:
        initialize_memory_tools(None)
    return _tools.save_memories(memory)


def save_relationship(memory: str) -> str:
    """
    保存用户关系到知识图谱

    当用户分享关系信息时使用此工具：
    - 人际关系（朋友、家人、同事）
    - 组织结构（谁向谁汇报）
    - 协作关系（谁和谁一起工作）
    - 任何涉及两个或多个实体之间关系的信息

    Args:
        memory: 要保存的关系描述

    Returns:
        确认消息，包含提取的关系
    """
    if not _tools:
        initialize_memory_tools(None)
    return _tools.save_relationship(memory)


def search_memories(query: str) -> str:
    """
    搜索与当前对话相关的记忆（完全借鉴 mem0 案例）

    当需要以下信息时使用此工具：
    - 用户之前提到的偏好
    - 历史对话中的重要信息
    - 需要参考用户背景来回答问题

    Args:
        query: 搜索查询，描述你想找到的记忆类型

    Returns:
        相关记忆的格式化列表
    """
    if not _tools:
        initialize_memory_tools(None)
    return _tools.search_memories(query)


def get_tool_definitions() -> list:
    """
    获取工具定义（OpenAI function calling 格式）

    Returns:
        工具定义列表
    """
    if not _tools:
        initialize_memory_tools(None)
    return _tools.get_tool_definitions()


def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    执行工具调用

    Args:
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    if not _tools:
        initialize_memory_tools(None)
    return _tools.execute_tool(tool_name, arguments)
