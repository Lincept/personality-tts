# """Mem0 记忆管理器（实现 MemoryStore 接口）。

# 说明：
# - 业务层应优先依赖 src.memory.store.MemoryStore 抽象接口。
# - 本类保留历史 API（search_memories/get_all_memories/clear_memories 等）以兼容旧调用。
# """

# from __future__ import annotations

# from typing import Any, Dict, List, Optional
# import os


# class Mem0Manager:
#     """Mem0 记忆管理器"""

#     def __init__(self, config: Dict):
#         """
#         初始化 Mem0

#         Args:
#             config: 配置字典，包含：
#                 - llm_api_key: OpenAI API Key（用于记忆提取）
#                 - llm_base_url: OpenAI Base URL
#                 - llm_model: 模型名称
#                 - enable_mem0: 是否启用 Mem0
#                 - enable_graph: 是否启用知识图谱（可选）
#                 - neo4j_url: Neo4j 连接 URL（可选）
#                 - neo4j_username: Neo4j 用户名（可选）
#                 - neo4j_password: Neo4j 密码（可选）
#         """
#         self.enabled = config.get("enable_mem0", False)
#         self.enable_graph = config.get("enable_graph", False)

#         if not self.enabled:
#             return

#         try:
#             from mem0 import Memory

#             # 构建 Mem0 配置
#             # 完全使用通义千问 API（LLM + Embedding）
#             mem0_config = {
#                 "llm": {
#                     "provider": "openai",
#                     "config": {
#                         "model": config.get("llm_model", "qwen-turbo"),
#                         "api_key": config.get("llm_api_key"),
#                         "openai_base_url": config.get("llm_base_url")
#                     }
#                 },
#                 "embedder": {
#                     "provider": "openai",
#                     "config": {
#                         "model": "text-embedding-v3",  # 通义千问 embedding 模型
#                         "api_key": config.get("llm_api_key"),
#                         "openai_base_url": config.get("llm_base_url"),
#                         "embedding_dims": 1024  # 通义千问支持的维度
#                     }
#                 },
#                 "vector_store": {
#                     "provider": "qdrant",
#                     "config": {
#                         "collection_name": "personality_tts_memory",
#                         "path": os.path.abspath("./data/qdrant"),  # 使用绝对路径
#                         "embedding_model_dims": 1024,  # 确保向量数据库使用正确的维度
#                         "on_disk": True  # 🔥 关键：启用持久化存储
#                     }
#                 }
#             }

#             # 如果启用图谱，添加 graph_store 配置
#             if self.enable_graph:
#                 neo4j_url = config.get("neo4j_url", "bolt://localhost:7687")
#                 neo4j_username = config.get("neo4j_username", "neo4j")
#                 neo4j_password = config.get("neo4j_password", "password")

#                 mem0_config["graph_store"] = {
#                     "provider": "neo4j",
#                     "config": {
#                         "url": neo4j_url,
#                         "username": neo4j_username,
#                         "password": neo4j_password
#                     }
#                 }
#                 print(f"✓ 知识图谱已启用 (Neo4j: {neo4j_url})")

#             self.memory = Memory.from_config(mem0_config)
#             # print("✓ Mem0 初始化成功")  # 静默初始化

#         except ImportError:
#             print("⚠️  警告: mem0ai 未安装，请运行: pip install mem0ai")
#             self.enabled = False
#         except Exception as e:
#             print(f"⚠️  Mem0 初始化失败: {e}")
#             self.enabled = False

#     def __bool__(self) -> bool:
#         # 兼容旧代码：if self.mem0_manager and self.mem0_manager.enabled
#         return bool(self.enabled)

#     @property
#     def supports_relationships(self) -> bool:
#         return bool(self.enabled and self.enable_graph)

#     def search(self, query: str, user_id: str, limit: int = 5) -> List[MemoryRecord]:
#         """通用检索接口：返回结构化结果，不在这里做展示格式化。"""
#         if not self.enabled:
#             return []

#         try:
#             results = self.memory.search(query=query, user_id=user_id, limit=limit)
#             items = results.get("results") or []
#             records: List[MemoryRecord] = []
#             for item in items:
#                 content = item.get("memory")
#                 if not content:
#                     continue
#                 records.append(
#                     MemoryRecord(
#                         content=str(content),
#                         id=item.get("id"),
#                         metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else None,
#                     )
#                 )
#             return records
#         except Exception:
#             return []

#     def save(
#         self,
#         memory: str,
#         user_id: str,
#         *,
#         kind: str = "fact",
#         metadata: Optional[Dict[str, Any]] = None,
#     ) -> None:
#         """通用保存接口。

#         - kind=relationship 且 enable_graph=True 时，尝试启用图谱抽取。
#         - 对外不抛异常，避免影响主对话链路。
#         """
#         if not self.enabled:
#             return

#         memory = (memory or "").strip()
#         if not memory:
#             return

#         try:
#             # 统一前缀，减少重复/不一致
#             if memory.startswith("User memory - "):
#                 memory_content = memory
#             else:
#                 memory_content = f"User memory - {memory}"

#             # 尽量兼容不同版本 mem0 的 add() 参数
#             add_kwargs: Dict[str, Any] = {"user_id": user_id}

#             # relationship 只有在启用图谱时才尝试开启；否则显式关闭以减少噪声
#             if self.enable_graph:
#                 add_kwargs["enable_graph"] = bool(kind == "relationship")

#             if metadata is not None:
#                 add_kwargs["metadata"] = metadata

#             self.memory.add(memory_content, **add_kwargs)
#             self._flush_to_disk()
#         except Exception:
#             return

#     def search_memories(self, query: str, user_id: str, limit: int = 5) -> str:
#         """
#         检索相关记忆

#         Args:
#             query: 查询文本（当前用户输入）
#             user_id: 用户ID
#             limit: 返回记忆数量

#         Returns:
#             格式化的记忆上下文字符串
#         """
#         if not self.enabled:
#             return ""

#         records = self.search(query=query, user_id=user_id, limit=limit)
#         if not records:
#             return ""
#         return "\n".join(f"- {r.content}" for r in records)

#     def add_conversation(self, user_input: str, assistant_response: str, user_id: str):
#         """
#         保存对话到记忆

#         Args:
#             user_input: 用户输入
#             assistant_response: 助手回复
#             user_id: 用户ID
#         """
#         if not self.enabled:
#             return

#         try:
#             messages = [
#                 {"role": "user", "content": user_input},
#                 {"role": "assistant", "content": assistant_response}
#             ]

#             # 对话消息形式交给 mem0 自己做提取
#             self.memory.add(messages, user_id=user_id)

#             # 强制刷新缓存到磁盘（确保数据持久化）
#             self._flush_to_disk()

#         except Exception as e:
#             print(f"⚠️  记忆保存失败: {e}")
#             import traceback
#             traceback.print_exc()

#     def _flush_to_disk(self):
#         """
#         强制将数据刷新到磁盘
#         """
#         try:
#             # 尝试访问 Qdrant 客户端并刷新
#             if hasattr(self.memory, 'vector_store') and hasattr(self.memory.vector_store, 'client'):
#                 client = self.memory.vector_store.client
#                 collection_name = self.memory.vector_store.collection_name

#                 # 1. 访问集合确保数据已写入
#                 if hasattr(client, 'get_collection'):
#                     client.get_collection(collection_name)

#                 # 2. 对于本地 Qdrant，显式调用 close() 触发持久化
#                 # 注意：不要在这里关闭，因为后续可能还需要使用
#                 # 只在程序退出时关闭
#                 pass
#         except Exception as e:
#             # 静默失败，不影响主流程
#             pass

#     def get_all(self, user_id: str) -> List[Dict[str, Any]]:
#         """
#         获取用户所有记忆

#         Args:
#             user_id: 用户ID

#         Returns:
#             记忆列表
#         """
#         if not self.enabled:
#             return []

#         try:
#             result = self.memory.get_all(user_id=user_id)
#             return result.get("results", [])
#         except Exception as e:
#             print(f"⚠️  获取记忆失败: {e}")
#             return []

#     def get_all_memories(self, user_id: str) -> List[Dict]:
#         # 兼容旧 API
#         return self.get_all(user_id=user_id)

#     def clear(self, user_id: str) -> None:
#         """
#         清除用户所有记忆

#         Args:
#             user_id: 用户ID
#         """
#         if not self.enabled:
#             return

#         try:
#             memories = self.get_all(user_id)
#             for mem in memories:
#                 self.memory.delete(memory_id=mem["id"])
#             print(f"✓ 已清除用户 {user_id} 的所有记忆")
#         except Exception as e:
#             print(f"⚠️  清除记忆失败: {e}")

#     def clear_memories(self, user_id: str):
#         # 兼容旧 API
#         return self.clear(user_id=user_id)

#     def close(self):
#         """
#         关闭 Mem0 连接，确保数据持久化
#         """
#         if not self.enabled:
#             return

#         try:
#             # 显式关闭 Qdrant 客户端以触发持久化
#             if hasattr(self.memory, 'vector_store') and hasattr(self.memory.vector_store, 'client'):
#                 client = self.memory.vector_store.client

#                 # 对于本地 Qdrant，调用 close() 方法
#                 if hasattr(client, 'close'):
#                     try:
#                         client.close()
#                         print("[Mem0] 已关闭 Qdrant 连接并持久化数据")
#                     except Exception as e:
#                         # 如果 close() 失败，尝试其他方法
#                         pass
#         except Exception as e:
#             # 静默失败
#             pass
