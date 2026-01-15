"""
Mem0 记忆工具 - 提供 LLM 可调用的记忆管理工具
借鉴 mem0 的工具化方法，让 LLM 主动管理记忆
"""
from typing import Dict, List, Optional
import json


class Mem0Tools:
    """为 LLM 提供记忆管理工具的包装类"""

    def __init__(self, mem0_manager, user_id: str = "default"):
        """
        初始化记忆工具

        Args:
            mem0_manager: Mem0Manager 实例
            user_id: 当前用户ID
        """
        self.mem0_manager = mem0_manager
        self.user_id = user_id

    def get_tool_definitions(self) -> List[Dict]:
        """
        获取工具定义（OpenAI function calling 格式）

        Returns:
            工具定义列表
        """
        if not self.mem0_manager or not self.mem0_manager.enabled:
            return []

        return [
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": """保存重要的用户信息到长期记忆。
当用户分享以下信息时应该调用此工具：
- 个人偏好（喜欢/不喜欢）
- 重要事实（姓名、职业、爱好等）
- 明确的需求或目标
- 任何值得记住的上下文信息

不要保存：
- 简单的问候或闲聊
- 临时性的信息
- 不重要的细节""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "memory_content": {
                                "type": "string",
                                "description": "要保存的记忆内容，用简洁的语言描述关键信息"
                            },
                            "category": {
                                "type": "string",
                                "description": "记忆类别（如：偏好、个人信息、目标、上下文等）",
                                "enum": ["preference", "personal_info", "goal", "context", "other"]
                            }
                        },
                        "required": ["memory_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_memories",
                    "description": """搜索相关的长期记忆。
当需要了解以下信息时应该调用此工具：
- 用户之前提到的偏好
- 历史对话中的重要信息
- 用户的背景或上下文
- 回答需要参考历史信息的问题

例如：
- 用户问"你还记得我喜欢什么吗？"
- 需要根据用户偏好给建议时
- 需要参考之前的对话内容时""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询，描述你想要找到的记忆类型"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回的记忆数量限制（默认5条）",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def execute_tool(self, tool_name: str, arguments: Dict) -> str:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            执行结果（字符串格式）
        """
        try:
            if tool_name == "save_memory":
                return self._save_memory(
                    arguments.get("memory_content", ""),
                    arguments.get("category", "other")
                )
            elif tool_name == "search_memories":
                return self._search_memories(
                    arguments.get("query", ""),
                    arguments.get("limit", 5)
                )
            else:
                return json.dumps({
                    "success": False,
                    "error": f"未知工具: {tool_name}"
                })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    def _save_memory(self, memory_content: str, category: str = "other") -> str:
        """
        保存记忆（内部方法）

        Args:
            memory_content: 记忆内容
            category: 记忆类别

        Returns:
            操作结果JSON字符串
        """
        if not memory_content.strip():
            return json.dumps({
                "success": False,
                "error": "记忆内容不能为空"
            })

        try:
            # 格式化记忆内容
            formatted_memory = f"[{category}] {memory_content}"

            # 保存到 Mem0
            messages = [
                {"role": "user", "content": memory_content}
            ]
            result = self.mem0_manager.memory.add(
                messages,
                user_id=self.user_id,
                metadata={"category": category}
            )

            print(f"[Mem0Tools] 已保存记忆: {memory_content[:50]}... (类别: {category})")

            return json.dumps({
                "success": True,
                "message": f"已保存记忆: {memory_content}",
                "category": category
            }, ensure_ascii=False)

        except Exception as e:
            print(f"[Mem0Tools] 保存记忆失败: {e}")
            return json.dumps({
                "success": False,
                "error": f"保存失败: {str(e)}"
            })

    def _search_memories(self, query: str, limit: int = 5) -> str:
        """
        搜索记忆（内部方法）

        Args:
            query: 搜索查询
            limit: 返回数量限制

        Returns:
            搜索结果JSON字符串
        """
        if not query.strip():
            return json.dumps({
                "success": False,
                "error": "搜索查询不能为空"
            })

        try:
            print(f"[Mem0Tools] 搜索记忆: {query}")

            results = self.mem0_manager.memory.search(
                query=query,
                user_id=self.user_id,
                limit=limit
            )

            if not results.get("results"):
                print(f"[Mem0Tools] 未找到相关记忆")
                return json.dumps({
                    "success": True,
                    "memories": [],
                    "message": "未找到相关记忆"
                }, ensure_ascii=False)

            memories = [
                {
                    "content": m["memory"],
                    "id": m.get("id", ""),
                    "created_at": m.get("created_at", "")
                }
                for m in results["results"]
            ]

            print(f"[Mem0Tools] 找到 {len(memories)} 条相关记忆")

            # 返回格式化的记忆列表
            memory_list = "\n".join([f"• {m['content']}" for m in memories])

            return json.dumps({
                "success": True,
                "memories": memories,
                "formatted_memories": memory_list,
                "count": len(memories)
            }, ensure_ascii=False)

        except Exception as e:
            print(f"[Mem0Tools] 搜索记忆失败: {e}")
            return json.dumps({
                "success": False,
                "error": f"搜索失败: {str(e)}"
            })


def create_memory_tools(mem0_manager, user_id: str = "default") -> Optional[Mem0Tools]:
    """
    创建记忆工具实例的便捷函数

    Args:
        mem0_manager: Mem0Manager 实例
        user_id: 用户ID

    Returns:
        Mem0Tools 实例，如果 mem0 未启用则返回 None
    """
    if not mem0_manager or not mem0_manager.enabled:
        return None

    return Mem0Tools(mem0_manager, user_id)
