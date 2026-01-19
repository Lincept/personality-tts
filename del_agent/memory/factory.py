"""src.memory.factory

集中创建 MemoryStore 的工厂方法。

后续你适配新记忆框架时，只需要：
1) 新增一个实现 MemoryStore 的类（例如 LangChainMemoryStore）
2) 在 create_memory_store() 里按配置选择即可
"""

from __future__ import annotations

from typing import Any, Dict

from .store import MemoryStore, NullMemoryStore


def create_memory_store(mem_cfg: Dict[str, Any]) -> MemoryStore:
    """根据配置创建记忆后端。

    当前支持：
    - mem0: 通过 enable_mem0 开关
    - none: 默认

    兼容：历史上项目只用 mem0_config.enable_mem0 控制启用/禁用。
    """

    if not mem_cfg:
        return NullMemoryStore()

    # 预留：未来可以引入 MEMORY_BACKEND=xxx
    backend = str(mem_cfg.get("backend", "mem0")).strip().lower()

    if backend in ("none", "null", "disabled"):
        return NullMemoryStore()

    if backend == "mem0":
        if not mem_cfg.get("enable_mem0", False):
            return NullMemoryStore()
        from .mem0_manager import Mem0Manager

        return Mem0Manager(mem_cfg)

    # 未知 backend：安全降级
    return NullMemoryStore()


def create_memory_manager(config: Dict[str, Any]):
    """创建 Memory Manager（兼容旧接口）
    
    Args:
        config: 配置字典
    
    Returns:
        MemoryStore 实例（Mem0Manager 或 NullMemoryStore）
    """
    return create_memory_store(config)
