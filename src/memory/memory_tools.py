"""
Memory Tools - 完全借鉴 mem0 案例的工具化记忆管理
参考: https://docs.mem0.ai/cookbooks/integrations/voice-first-ai-companion

支持两种存储模式：
1. save_memories - 保存事实到向量数据库
2. save_relationship - 保存关系到知识图谱
"""
from typing import Optional

# 全局变量，将在初始化时设置
mem0_client = None
USER_ID = "default_user"
VERBOSE = False  # 是否显示详细日志


def initialize_memory_tools(mem0_manager, user_id: str = "default_user", verbose: bool = False):
    """
    初始化记忆工具（类似 mem0 案例）

    Args:
        mem0_manager: Mem0Manager 实例
        user_id: 用户 ID
        verbose: 是否显示详细日志（默认 False）
    """
    global mem0_client, USER_ID, VERBOSE
    mem0_client = mem0_manager
    USER_ID = user_id
    VERBOSE = verbose


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
    if VERBOSE:
        print(f"[Mem0] 保存记忆（向量）: {memory} (用户: {USER_ID})")

    if not mem0_client or not mem0_client.enabled:
        return "Memory system is not enabled"

    try:
        # 格式化记忆内容
        memory_content = f"User memory - {memory}"

        # 保存到向量数据库（不启用图谱）
        result = mem0_client.memory.add(
            memory_content,
            user_id=USER_ID,
            enable_graph=False  # 明确指定不使用图谱
        )

        # 强制刷新到磁盘
        mem0_client._flush_to_disk()

        if VERBOSE:
            print(f"[Mem0] 保存成功（向量存储）")

        return f"I've saved your memory: {memory}"

    except Exception as e:
        if VERBOSE:
            print(f"[Mem0] 保存失败: {e}")
        return f"Failed to save memory: {str(e)}"


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
    if VERBOSE:
        print(f"[Mem0] 保存关系（图谱）: {memory} (用户: {USER_ID})")

    if not mem0_client or not mem0_client.enabled:
        return "Memory system is not enabled"

    if not mem0_client.enable_graph:
        # 如果图谱未启用，降级到向量存储
        return save_memories(memory)

    try:
        # 格式化记忆内容
        memory_content = f"User memory - {memory}"

        # 保存到向量数据库 + 知识图谱
        result = mem0_client.memory.add(
            memory_content,
            user_id=USER_ID,
            enable_graph=True  # 🔥 启用图谱提取
        )

        # 强制刷新到磁盘
        mem0_client._flush_to_disk()

        # 检查是否提取到关系
        relations = result.get('relations', [])

        if VERBOSE:
            print(f"[Mem0] 保存成功（向量 + 图谱）")
            if relations:
                print(f"[Mem0] 提取到 {len(relations)} 个关系:")
                for rel in relations[:3]:
                    print(f"  - {rel.get('source')} → {rel.get('relationship')} → {rel.get('target')}")

        # 构建返回消息
        if relations:
            rel_summary = ", ".join([
                f"{rel.get('source')} {rel.get('relationship')} {rel.get('target')}"
                for rel in relations[:2]
            ])
            return f"I've saved the relationship: {memory}. Extracted: {rel_summary}"
        else:
            return f"I've saved your memory: {memory}"

    except Exception as e:
        if VERBOSE:
            print(f"[Mem0] 保存失败: {e}")
        return f"Failed to save memory: {str(e)}"


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
    if VERBOSE:
        print(f"[Mem0] 搜索记忆: {query} (用户: {USER_ID})")

    if not mem0_client or not mem0_client.enabled:
        return "Memory system is not enabled"

    try:
        results = mem0_client.memory.search(
            query,
            user_id=USER_ID,
            limit=5,
            threshold=0.7,  # 更高的阈值以获得更相关的结果
        )

        # 格式化并返回结果（类似 mem0 案例）
        if not results.get('results', []):
            if VERBOSE:
                print(f"[Mem0] 未找到相关记忆")
            return "I don't have any relevant memories about this topic."

        memories = [f"• {result['memory']}" for result in results.get('results', [])]

        if VERBOSE:
            print(f"[Mem0] 找到 {len(memories)} 条相关记忆")

        return "Here's what I remember that might be relevant:\n" + "\n".join(memories)

    except Exception as e:
        if VERBOSE:
            print(f"[Mem0] 搜索失败: {e}")
        return f"Failed to search memories: {str(e)}"


def get_tool_definitions() -> list:
    """
    获取工具定义（OpenAI function calling 格式）

    Returns:
        工具定义列表
    """
    # 检查是否启用图谱
    graph_enabled = mem0_client and mem0_client.enabled and mem0_client.enable_graph

    tools = [
        {
            "type": "function",
            "function": {
                "name": "save_memories",
                "description": """保存用户的事实性记忆到向量数据库。

**何时使用此工具**：
- 用户分享个人偏好："我喜欢攀岩"、"我不喜欢辣的"
- 用户分享个人信息："我叫 Thomas"、"我是工程师"
- 用户分享事实："我住在北京"、"我在学 Python"
- 用户表达目标或需求："我想减肥"、"我要学英语"

**不要使用此工具**：
- 简单的问候或闲聊
- 临时信息
- 涉及人际关系的信息（使用 save_relationship）

**示例**：
- ✅ "我叫 Thomas" → save_memories("用户叫 Thomas")
- ✅ "我喜欢攀岩" → save_memories("用户喜欢攀岩")
- ❌ "Alice 是我的朋友" → 应该使用 save_relationship""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "memory": {
                            "type": "string",
                            "description": "要保存的事实性记忆（简洁清晰）"
                        }
                    },
                    "required": ["memory"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_memories",
                "description": """搜索与当前对话相关的记忆。

**何时使用此工具**：
- 用户询问"你还记得吗"、"我之前说过什么"
- 需要参考用户的历史信息来回答问题
- 需要根据用户偏好提供个性化建议
- 想要提供基于历史的个性化回复

**示例**：
- 用户："你还记得我叫什么吗？" → search_memories("用户的名字")
- 用户："我喜欢什么运动？" → search_memories("用户喜欢的运动")""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询，描述你想找到的记忆类型"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    # 只有在图谱启用时才添加 save_relationship 工具
    if graph_enabled:
        tools.insert(1, {
            "type": "function",
            "function": {
                "name": "save_relationship",
                "description": """保存实体之间的关系到知识图谱。

**何时使用此工具**：
- 用户分享人际关系："Alice 是我的朋友"、"Bob 是我的同事"
- 用户描述组织结构："Bob 向 Rachel 汇报"、"Rachel 是团队经理"
- 用户描述协作关系："Emma 和 David 一起做项目"
- 任何涉及两个或多个实体之间关系的信息

**不要使用此工具**：
- 单纯的事实信息（使用 save_memories）
- 不涉及关系的描述

**示例**：
- ✅ "Alice 是我的朋友" → save_relationship("Alice 是我的朋友")
- ✅ "Bob 向 Rachel 汇报" → save_relationship("Bob 向 Rachel 汇报")
- ❌ "我喜欢 Alice" → 应该使用 save_memories

**自动提取**：
系统会自动提取实体和关系：
- "Alice 是我的朋友" → Thomas --[朋友]--> Alice
- "Bob 向 Rachel 汇报" → Bob --[汇报]--> Rachel""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "memory": {
                            "type": "string",
                            "description": "要保存的关系描述（完整句子）"
                        }
                    },
                    "required": ["memory"]
                }
            }
        })

    return tools


def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    执行工具调用

    Args:
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    if tool_name == "save_memories":
        return save_memories(arguments.get("memory", ""))
    elif tool_name == "save_relationship":
        return save_relationship(arguments.get("memory", ""))
    elif tool_name == "search_memories":
        return search_memories(arguments.get("query", ""))
    else:
        return f"Unknown tool: {tool_name}"
