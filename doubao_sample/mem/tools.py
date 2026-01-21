# """src.memory.tools

# 统一的“记忆工具层”（Function Calling / tool calling）。

# 历史上仓库里存在两套重复实现：
# - memory_tools.py（函数 + 全局变量）
# - mem0_tools.py（类封装，但工具名/返回格式不同）

# 这里提供一个框架无关的实现：只依赖 MemoryStore。
# """

# from __future__ import annotations

# from typing import Any, Dict, List, Optional

# class MemoryTools:
#     def __init__(self, memory_store: MemoryStore, user_id: str = "default_user", verbose: bool = False):
#         self.memory_store = memory_store
#         self.user_id = user_id
#         self.verbose = verbose

#     def get_tool_definitions(self) -> List[Dict[str, Any]]:
#         if not self.memory_store or not getattr(self.memory_store, "enabled", False):
#             return []

#         tools: List[Dict[str, Any]] = [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "save_memories",
#                     "description": """保存用户的事实性记忆到长期记忆库（向量存储优先）。

# 何时使用：用户分享个人偏好/个人信息/长期目标等值得长期记住的事实。
# 不要使用：简单寒暄、临时信息。""",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "memory": {"type": "string", "description": "要保存的事实性记忆（简洁清晰）"}
#                         },
#                         "required": ["memory"],
#                     },
#                 },
#             },
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "search_memories",
#                     "description": """搜索与当前对话相关的历史记忆。""",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "query": {"type": "string", "description": "搜索查询，描述想找到的记忆类型"}
#                         },
#                         "required": ["query"],
#                     },
#                 },
#             },
#         ]

#         if getattr(self.memory_store, "supports_relationships", False):
#             tools.insert(
#                 1,
#                 {
#                     "type": "function",
#                     "function": {
#                         "name": "save_relationship",
#                         "description": """保存实体之间的关系类记忆到知识图谱（如果后端支持）。

# 何时使用：朋友/同事/隶属/汇报/协作等关系描述。""",
#                         "parameters": {
#                             "type": "object",
#                             "properties": {
#                                 "memory": {"type": "string", "description": "关系描述（完整句子）"}
#                             },
#                             "required": ["memory"],
#                         },
#                     },
#                 },
#             )

#         return tools

#     def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
#         if tool_name == "save_memories":
#             return self.save_memories(arguments.get("memory", ""))
#         if tool_name == "save_relationship":
#             return self.save_relationship(arguments.get("memory", ""))
#         if tool_name == "search_memories":
#             return self.search_memories(arguments.get("query", ""))
#         return f"Unknown tool: {tool_name}"

#     def save_memories(self, memory: str) -> str:
#         if not self.memory_store or not getattr(self.memory_store, "enabled", False):
#             return "Memory system is not enabled"

#         memory = (memory or "").strip()
#         if not memory:
#             return "Memory content is empty"

#         if self.verbose:
#             print(f"[MemoryTools] save_memories: {memory} (user={self.user_id})")

#         try:
#             self.memory_store.save(memory, user_id=self.user_id, kind="fact")
#             return f"I've saved your memory: {memory}"
#         except Exception as e:
#             return f"Failed to save memory: {str(e)}"

#     def save_relationship(self, memory: str) -> str:
#         if not self.memory_store or not getattr(self.memory_store, "enabled", False):
#             return "Memory system is not enabled"

#         memory = (memory or "").strip()
#         if not memory:
#             return "Memory content is empty"

#         if self.verbose:
#             print(f"[MemoryTools] save_relationship: {memory} (user={self.user_id})")

#         try:
#             # 如果后端不支持 relationship，降级到 fact
#             kind = "relationship" if getattr(self.memory_store, "supports_relationships", False) else "fact"
#             self.memory_store.save(memory, user_id=self.user_id, kind=kind)
#             return f"I've saved the relationship: {memory}"
#         except Exception as e:
#             return f"Failed to save relationship: {str(e)}"

#     def search_memories(self, query: str) -> str:
#         if not self.memory_store or not getattr(self.memory_store, "enabled", False):
#             return "Memory system is not enabled"

#         query = (query or "").strip()
#         if not query:
#             return "Query is empty"

#         if self.verbose:
#             print(f"[MemoryTools] search_memories: {query} (user={self.user_id})")

#         try:
#             records = self.memory_store.search(query=query, user_id=self.user_id, limit=5)
#             if not records:
#                 return "I don't have any relevant memories about this topic."

#             memories = [f"• {r.content}" for r in records]
#             return "Here's what I remember that might be relevant:\n" + "\n".join(memories)
#         except Exception as e:
#             return f"Failed to search memories: {str(e)}"
