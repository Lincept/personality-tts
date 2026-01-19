"""
Storage 模块 - 存储与检索接入层

支持两种存储后端：
- JSON: 本地文件存储，无外部依赖
- Mem0: 基于向量数据库的语义检索（需要 API）
- Hybrid: 混合存储（同时使用 JSON 和 Mem0）
"""

from .vector_store import VectorStore, VectorRecord
from .knowledge_graph import KnowledgeGraph, KnowledgeNode, KnowledgeRelation
from .unified_store import (
    KnowledgeStore,
    KnowledgeRecord,
    JsonKnowledgeStore,
    Mem0KnowledgeStore,
    HybridKnowledgeStore,
    create_knowledge_store,
)

__all__ = [
    # 旧接口（保持兼容）
    'VectorStore',
    'VectorRecord',
    'KnowledgeGraph',
    'KnowledgeNode',
    'KnowledgeRelation',
    # 新统一接口
    'KnowledgeStore',
    'KnowledgeRecord',
    'JsonKnowledgeStore',
    'Mem0KnowledgeStore',
    'HybridKnowledgeStore',
    'create_knowledge_store',
]
