"""
上下文构建器 - 整合所有层生成最终上下文
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from .layers.agent_personality import AgentPersonality
from .layers.agent_state import AgentState
from .layers.event_layer import EventLayer
from .layers.user_profile import UserProfileManager


class ContextBuilder:
    """
    动态上下文构建器

    整合 6 层上下文，生成完整的 system prompt
    """

    def __init__(
        self,
        agent_id: str,
        mbti_type: str = "ENFP",
        mem0_manager=None,
        llm_client=None,
        base_role_prompt: str = "",
        batch_interval: int = 5,       # 批量处理间隔
        strategy_interval: int = 10    # 策略更新间隔
    ):
        """
        初始化上下文构建器

        Args:
            agent_id: Agent 标识
            mbti_type: Agent 的 MBTI 类型
            mem0_manager: Mem0 管理器
            llm_client: LLM 客户端
            base_role_prompt: 基础角色 prompt
            batch_interval: 批量处理间隔（对话次数）
            strategy_interval: 策略更新间隔（对话次数）
        """
        self.agent_id = agent_id
        self.base_role_prompt = base_role_prompt
        self.llm_client = llm_client
        self.batch_interval = batch_interval

        # 初始化各层
        self.personality = AgentPersonality(agent_id, mbti_type)
        self.state = AgentState(agent_id)
        self.events = EventLayer(agent_id, mem0_manager, llm_client=llm_client)
        self.user_profiles = UserProfileManager(
            llm_client=llm_client,
            strategy_update_interval=strategy_interval
        )

        # 当前会话ID
        self.current_session_id = str(uuid.uuid4())

    def build_context(
        self,
        user_id: str,
        user_input: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        构建完整上下文

        构建顺序（从上到下注入）：
        1. 基础角色定义
        2. Agent 个性（MBTI + 说话风格）
        3. 用户画像（一开始就注入）
        4. Agent 状态（时间 + 疲劳）
        5. 活动摘要（默认注入）

        Args:
            user_id: 用户ID
            user_input: 用户输入
            conversation_history: 对话历史

        Returns:
            完整的 system prompt
        """
        # 更新状态
        self.state.on_message()

        # 获取用户画像
        user_profile = self.user_profiles.get_or_create_profile(user_id)

        # 根据用户画像调整个性
        self.personality.adapt_for_user(user_id, user_profile)

        # 构建上下文片段
        context_parts = []

        # Layer 1: 基础角色定义
        if self.base_role_prompt:
            context_parts.append(self.base_role_prompt)

        # Layer 2: Agent 个性
        personality_context = self.personality.generate_personality_prompt(user_id)
        context_parts.append(personality_context)

        # Layer 3: 用户画像
        profile_context = self.user_profiles.generate_profile_context(user_id)
        context_parts.append(profile_context)

        # Layer 4: Agent 状态
        state_context = self.state.generate_state_prompt()
        context_parts.append(state_context)

        # Layer 5: 活动摘要
        event_context = self.events.generate_event_context()
        context_parts.append(event_context)

        # 添加当前时间
        context_parts.append(f"\n【当前时间】{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")

        # 合并所有上下文
        full_context = "\n\n".join(context_parts)

        return full_context

    def on_conversation_turn(
        self,
        user_id: str,
        user_input: str,
        assistant_response: str,
        conversation_history: List[Dict]
    ):
        """
        对话轮次结束后的处理

        执行以下操作：
        1. 累加计数
        2. 添加到事件缓存
        3. 更新用户画像基本信息
        4. 检查是否需要批量处理

        Args:
            user_id: 用户ID
            user_input: 用户输入
            assistant_response: 助手回复
            conversation_history: 完整对话历史
        """
        # 添加到事件缓存
        self.events.add_conversation_to_buffer(user_input, assistant_response, user_id)

        # 更新用户画像基本信息
        self.user_profiles.update_after_conversation(user_id, user_input, assistant_response)

        # 检查是否需要批量处理（每5次对话）
        if self.state.should_trigger_batch_processing(self.batch_interval):
            self._do_batch_processing(user_id, conversation_history)

        # 保存状态
        self.state.save_state()

    def _do_batch_processing(self, user_id: str, conversation_history: List[Dict]):
        """执行批量处理"""
        # 处理事件缓存
        self.events.process_batch()
        self.events.save_summary()

        # 检查是否需要更新策略（每10次对话）
        if self.user_profiles.should_update_strategy(user_id):
            self.user_profiles.update_strategy(user_id, conversation_history)

        # 保存用户画像
        self.user_profiles.save_profile(user_id)

    def on_session_end(
        self,
        user_id: str,
        conversation_history: List[Dict]
    ):
        """
        会话结束时的处理

        执行更耗时的操作：
        1. 处理剩余的事件缓存
        2. 生成对话摘要
        3. 分析用户个性（如果对话足够长）
        4. 保存所有状态

        Args:
            user_id: 用户ID
            conversation_history: 完整对话历史
        """
        # 处理剩余的事件缓存
        if self.events.get_buffer_size() > 0:
            self.events.process_batch()

        # 添加对话摘要
        self.user_profiles.add_conversation_summary(
            user_id, self.current_session_id, conversation_history
        )

        # 分析用户个性（如果对话足够长）
        if len(conversation_history) >= 10:
            self.user_profiles.analyze_user_personality(user_id, conversation_history)

        # 保存所有状态
        self.state.save_state()
        self.events.save_summary()
        self.user_profiles.save_profile(user_id)

        # 生成新的会话ID
        self.current_session_id = str(uuid.uuid4())

    def search_events(self, query: str, time_range: Optional[str] = None) -> List[str]:
        """
        搜索历史事件

        Args:
            query: 搜索查询
            time_range: 时间范围

        Returns:
            相关事件列表
        """
        return self.events.search_events(query, time_range)

    def get_user_profile(self, user_id: str):
        """获取用户画像"""
        return self.user_profiles.get_or_create_profile(user_id)

    def get_agent_state(self):
        """获取 Agent 状态"""
        return self.state.state

    def reset_session(self):
        """重置会话状态"""
        self.state.reset_session()
        self.current_session_id = str(uuid.uuid4())
