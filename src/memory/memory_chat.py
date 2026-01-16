"""
两阶段记忆增强对话 - 使用结构化输出优化记忆管理

方案特点：
1. 第一阶段：分析用户意图，判断是否检索/存储，生成语义化检索词
2. 第二阶段：基于检索结果生成最终回复
3. 存储通过 Hook 异步执行，结果写入日志
4. 使用 qwen3-max 的 JSON Object 模式
"""

import json
import logging
from typing import Optional, List, Dict, Any, Generator
from dataclasses import dataclass, field
from openai import OpenAI

# 配置日志
logger = logging.getLogger("memory_chat")


# ============================================
# 数据结构定义
# ============================================

@dataclass
class MemoryItem:
    """要保存的记忆项"""
    type: str  # "fact" 或 "relationship"
    content: str


@dataclass
class AnalysisResult:
    """第一阶段分析结果"""
    thinking: str
    need_memory_search: bool
    memory_search_query: Optional[str] = None
    should_save_memory: bool = False
    memory_to_save: Optional[MemoryItem] = None


@dataclass
class FinalResponse:
    """第二阶段最终回复"""
    response: str


# ============================================
# System Prompts
# ============================================

ANALYSIS_SYSTEM_PROMPT = """你是一个记忆分析助手。你的任务是分析用户的输入，判断：
1. 是否需要检索历史记忆才能回答
2. 用户是否分享了值得保存的信息

## 角色背景
{role_description}

## 输出格式（必须是 JSON）
{{
    "thinking": "一步步分析用户意图...",
    "need_memory_search": true或false,
    "memory_search_query": "语义化检索词（如果需要检索）",
    "should_save_memory": true或false,
    "memory_to_save": {{
        "type": "fact 或 relationship",
        "content": "要保存的内容"
    }}
}}

## 检索判断规则
需要检索的情况：
- 用户问"你还记得我叫什么吗" → need_memory_search=true, query="用户的名字"
- 用户问"我之前说我喜欢什么" → need_memory_search=true, query="用户的偏好喜好"
- 用户问"你记得我的工作吗" → need_memory_search=true, query="用户的职业工作"
- 用户问"刚才我和你说过什么" → need_memory_search=true, query="用户最近分享的个人信息"
- 需要用户历史信息才能个性化回答

不需要检索的情况：
- "你好"、"谢谢" → 闲聊
- "帮我写段代码" → 不涉及个人信息
- 一般性知识问答

## 检索词生成规则（重要！）
生成语义化的检索词，而不是用户的原话：
❌ 错误："刚才我说过什么" → 无法匹配存储的记忆
❌ 错误："用户之前的对话" → 太泛
✅ 正确："用户的名字"
✅ 正确："用户喜欢的运动"
✅ 正确："用户的工作职业"
✅ 正确："用户最近分享的个人信息"

## 存储判断规则
需要存储的信息：
- "我叫 Thomas" → type=fact, content="用户名字是 Thomas"
- "我喜欢攀岩" → type=fact, content="用户喜欢攀岩运动"
- "我是软件工程师" → type=fact, content="用户职业是软件工程师"
- "Alice 是我朋友" → type=relationship, content="Alice 是用户的朋友"
- "Bob 是我同事" → type=relationship, content="Bob 是用户的同事"

不需要存储的信息：
- "你好"、"谢谢"、"再见"
- "今天天气怎么样"
- 一般性知识问答
- 临时性问题
"""


RESPONSE_SYSTEM_PROMPT = """你是一个友好的 AI 助手。

## 角色设定
{role_description}

## 已知的用户信息
{retrieved_memories}

## 输出格式（必须是 JSON）
{{
    "response": "你的回复内容"
}}

请根据用户信息和对话上下文，生成自然、友好的回复。
如果有用户的历史信息，请恰当地使用它们来个性化回复。
不要生硬地复述记忆内容，而是自然地融入对话。
"""


RESPONSE_SYSTEM_PROMPT_STREAM = """你是一个友好的 AI 助手。

## 角色设定
{role_description}

## 已知的用户信息
{retrieved_memories}

请根据用户信息和对话上下文，生成自然、友好的回复。
如果有用户的历史信息，请恰当地使用它们来个性化回复。
不要生硬地复述记忆内容，而是自然地融入对话。
直接输出回复内容，不需要任何格式标记。
"""


# ============================================
# 核心类
# ============================================

class MemoryEnhancedChat:
    """两阶段记忆增强对话"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen3-max",
        mem0_manager = None,
        user_id: str = "default_user",
        role_description: str = "你是一个友好的 AI 助手",
        verbose: bool = False,
        context_builder = None  # 新增：上下文构建器
    ):
        """
        初始化记忆增强对话

        Args:
            api_key: API Key
            base_url: API Base URL
            model: 模型名称（需要支持 JSON Object 模式）
            mem0_manager: Mem0Manager 实例
            user_id: 用户 ID
            role_description: 角色描述
            verbose: 是否输出详细日志到控制台
            context_builder: ContextBuilder 实例（可选，用于分层上下文）
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.mem0 = mem0_manager
        self.user_id = user_id
        self.role_description = role_description
        self.verbose = verbose
        self.context_builder = context_builder  # 新增

        # 配置日志级别
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def chat(self, user_input: str, history: List[Dict] = None) -> str:
        """
        完整对话流程（非流式）

        Args:
            user_input: 用户输入
            history: 对话历史

        Returns:
            最终回复文本
        """
        history = history or []

        # ========== 第一阶段：意图分析 ==========
        analysis = self._analyze_intent(user_input, history)

        if self.verbose:
            print(f"[分析] thinking: {analysis.thinking}")
            print(f"[分析] need_search: {analysis.need_memory_search}, save: {analysis.should_save_memory}")

        logger.info(f"[分析] need_search={analysis.need_memory_search}, save={analysis.should_save_memory}")
        logger.debug(f"[分析] thinking: {analysis.thinking}")

        # ========== 处理存储（Hook）==========
        if analysis.should_save_memory and analysis.memory_to_save:
            self._save_memory_hook(analysis.memory_to_save)

        # ========== 处理检索 ==========
        retrieved_memories = ""
        if analysis.need_memory_search and analysis.memory_search_query:
            retrieved_memories = self._search_memories(analysis.memory_search_query)

            if self.verbose:
                print(f"[检索] query: {analysis.memory_search_query}")
                print(f"[检索] 结果: {retrieved_memories}")

            logger.info(f"[检索] query={analysis.memory_search_query}")
            logger.info(f"[检索] 结果: {retrieved_memories}")

        # ========== 第二阶段：生成回复 ==========
        final_response = self._generate_response(
            user_input,
            history,
            retrieved_memories
        )

        return final_response.response

    def chat_stream(self, user_input: str, history: List[Dict] = None) -> Generator[str, None, None]:
        """
        流式对话流程（支持 TTS 实时播放）

        Args:
            user_input: 用户输入
            history: 对话历史

        Yields:
            回复文本片段
        """
        history = history or []

        # ========== 第一阶段：意图分析（非流式）==========
        analysis = self._analyze_intent(user_input, history)

        logger.info(f"[分析] need_search={analysis.need_memory_search}, save={analysis.should_save_memory}")

        # ========== 处理存储（Hook）==========
        if analysis.should_save_memory and analysis.memory_to_save:
            self._save_memory_hook(analysis.memory_to_save)

        # ========== 处理检索 ==========
        retrieved_memories = ""
        if analysis.need_memory_search and analysis.memory_search_query:
            retrieved_memories = self._search_memories(analysis.memory_search_query)
            logger.info(f"[检索] query={analysis.memory_search_query}, 结果: {retrieved_memories}")

        # ========== 第二阶段：流式生成回复 ==========
        yield from self._generate_response_stream(
            user_input,
            history,
            retrieved_memories
        )

    def _analyze_intent(self, user_input: str, history: List[Dict]) -> AnalysisResult:
        """
        第一阶段：分析用户意图

        独立的上下文：对话历史 + 用户输入 + 角色信息
        """
        system_prompt = ANALYSIS_SYSTEM_PROMPT.format(
            role_description=self.role_description
        )

        # 构建消息（仅包含必要信息）
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 添加最近几轮对话历史（限制数量避免 token 过多）
        recent_history = history[-6:] if len(history) > 6 else history
        for msg in recent_history:
            messages.append(msg)

        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        try:
            # 调用 LLM（JSON Object 模式）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,  # 低温度，更稳定
                max_tokens=500
            )

            # 解析结果
            content = response.choices[0].message.content
            data = json.loads(content)

            # 解析 memory_to_save
            memory_to_save = None
            if data.get("memory_to_save"):
                mem_data = data["memory_to_save"]
                memory_to_save = MemoryItem(
                    type=mem_data.get("type", "fact"),
                    content=mem_data.get("content", "")
                )

            return AnalysisResult(
                thinking=data.get("thinking", ""),
                need_memory_search=data.get("need_memory_search", False),
                memory_search_query=data.get("memory_search_query"),
                should_save_memory=data.get("should_save_memory", False),
                memory_to_save=memory_to_save
            )

        except Exception as e:
            logger.error(f"[分析错误] {e}")
            # 返回默认值，不中断流程
            return AnalysisResult(
                thinking=f"分析出错: {e}",
                need_memory_search=False,
                should_save_memory=False
            )

    def _generate_response(
        self,
        user_input: str,
        history: List[Dict],
        retrieved_memories: str
    ) -> FinalResponse:
        """
        第二阶段：生成最终回复（非流式）
        """
        system_prompt = RESPONSE_SYSTEM_PROMPT.format(
            role_description=self.role_description,
            retrieved_memories=retrieved_memories if retrieved_memories else "（无历史记忆）"
        )

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 完整对话历史
        for msg in history:
            messages.append(msg)

        messages.append({"role": "user", "content": user_input})

        try:
            # 调用 LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return FinalResponse(response=data.get("response", ""))

        except Exception as e:
            logger.error(f"[回复错误] {e}")
            return FinalResponse(response=f"抱歉，出现了一些问题: {e}")

    def _generate_response_stream(
        self,
        user_input: str,
        history: List[Dict],
        retrieved_memories: str
    ) -> Generator[str, None, None]:
        """
        第二阶段：流式生成回复（支持 TTS）

        注意：流式模式不使用 JSON Object，直接输出文本
        """
        # 如果有 context_builder，使用分层上下文
        if self.context_builder:
            dynamic_context = self.context_builder.build_context(
                user_id=self.user_id,
                user_input=user_input,
                conversation_history=history
            )
            system_prompt = RESPONSE_SYSTEM_PROMPT_STREAM.format(
                role_description=dynamic_context,
                retrieved_memories=retrieved_memories if retrieved_memories else "（无历史记忆）"
            )
        else:
            system_prompt = RESPONSE_SYSTEM_PROMPT_STREAM.format(
                role_description=self.role_description,
                retrieved_memories=retrieved_memories if retrieved_memories else "（无历史记忆）"
            )

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 完整对话历史
        for msg in history:
            messages.append(msg)

        messages.append({"role": "user", "content": user_input})

        try:
            # 流式调用（不使用 response_format）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"[流式回复错误] {e}")
            yield f"抱歉，出现了一些问题: {e}"

    def _search_memories(self, query: str) -> str:
        """检索记忆"""
        if not self.mem0 or not self.mem0.enabled:
            return ""

        try:
            results = self.mem0.memory.search(
                query=query,
                user_id=self.user_id,
                limit=5
            )

            if not results.get("results"):
                logger.info(f"[检索] 未找到相关记忆")
                return ""

            memories = [f"• {r['memory']}" for r in results["results"]]
            return "\n".join(memories)

        except Exception as e:
            logger.error(f"[检索错误] {e}")
            return ""

    def _save_memory_hook(self, memory_item: MemoryItem):
        """
        存储 Hook

        保存记忆到 Mem0，结果写入日志
        """
        if not self.mem0 or not self.mem0.enabled:
            logger.warning("[存储] Mem0 未启用")
            return

        if not memory_item.content:
            return

        try:
            # 格式化记忆内容
            memory_content = f"User memory - {memory_item.content}"

            # 调用 mem0 保存（不传 enable_graph，由 Mem0Manager 配置决定）
            result = self.mem0.memory.add(
                memory_content,
                user_id=self.user_id
            )

            # 强制刷新到磁盘
            self.mem0._flush_to_disk()

            # 结果写入日志
            logger.info(f"[存储成功] type={memory_item.type}, content={memory_item.content}")
            logger.debug(f"[存储详情] {result}")

            if self.verbose:
                print(f"[存储] type={memory_item.type}, content={memory_item.content}")

        except Exception as e:
            logger.error(f"[存储失败] {e}")

    def on_conversation_turn(
        self,
        user_input: str,
        assistant_response: str,
        history: List[Dict]
    ):
        """
        对话轮次结束后调用

        用于更新 ContextBuilder 的状态

        Args:
            user_input: 用户输入
            assistant_response: 助手回复
            history: 对话历史
        """
        if self.context_builder:
            self.context_builder.on_conversation_turn(
                user_id=self.user_id,
                user_input=user_input,
                assistant_response=assistant_response,
                conversation_history=history
            )

    def on_session_end(self, history: List[Dict]):
        """
        会话结束时调用

        用于执行 ContextBuilder 的会话结束处理

        Args:
            history: 完整对话历史
        """
        if self.context_builder:
            self.context_builder.on_session_end(
                user_id=self.user_id,
                conversation_history=history
            )


# ============================================
# 便捷函数
# ============================================

def create_memory_chat(
    config: Dict[str, Any],
    role_description: str = "你是一个友好的 AI 助手",
    verbose: bool = False
) -> MemoryEnhancedChat:
    """
    从配置创建 MemoryEnhancedChat 实例

    Args:
        config: 配置字典（来自 ConfigLoader）
        role_description: 角色描述
        verbose: 是否输出详细日志

    Returns:
        MemoryEnhancedChat 实例
    """
    from .mem0_manager import Mem0Manager

    # 获取 LLM 配置
    llm_config = config.get("openai_compatible", {})

    # 获取 Mem0 配置
    mem0_config = config.get("mem0", {})
    mem0_manager = None
    if mem0_config.get("enable_mem0", False):
        mem0_manager = Mem0Manager(mem0_config)

    # 获取用户 ID
    user_id = mem0_config.get("user_id", "default_user")

    return MemoryEnhancedChat(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        model=llm_config.get("model", "qwen3-max"),
        mem0_manager=mem0_manager,
        user_id=user_id,
        role_description=role_description,
        verbose=verbose
    )
