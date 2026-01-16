"""
用户画像层 - 管理用户个性分析和对话概述
"""
import json
import os
from datetime import datetime
from typing import Optional, Dict, List

from ..models.user_profile import UserProfile, UserPersonality, ConversationSummary


class UserProfileManager:
    """用户画像管理器"""

    def __init__(
        self,
        profile_dir: str = "data/context/user_profiles",
        llm_client=None,
        strategy_update_interval: int = 10  # 每10次对话评估一次策略
    ):
        """
        初始化用户画像管理器

        Args:
            profile_dir: 画像存储目录
            llm_client: LLM 客户端
            strategy_update_interval: 策略更新间隔（对话次数）
        """
        self.profile_dir = profile_dir
        self.llm_client = llm_client
        self.strategy_update_interval = strategy_update_interval

        # 内存中的用户画像缓存
        self._profiles: Dict[str, UserProfile] = {}

        # 本次会话的交互计数
        self._interaction_counts: Dict[str, int] = {}

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """获取或创建用户画像"""
        if user_id in self._profiles:
            return self._profiles[user_id]

        profile_file = os.path.join(self.profile_dir, f"{user_id}_profile.json")

        if os.path.exists(profile_file):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    profile = UserProfile.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                profile = UserProfile(user_id=user_id)
        else:
            profile = UserProfile(user_id=user_id)

        self._profiles[user_id] = profile
        self._interaction_counts[user_id] = 0
        return profile

    def update_after_conversation(
        self,
        user_id: str,
        user_input: str,
        assistant_response: str
    ):
        """
        对话后更新用户画像（基本更新）

        Args:
            user_id: 用户ID
            user_input: 用户输入
            assistant_response: 助手回复
        """
        profile = self.get_or_create_profile(user_id)
        profile.updated_at = datetime.now()
        profile.total_interactions += 1

        self._interaction_counts[user_id] = self._interaction_counts.get(user_id, 0) + 1

    def should_update_strategy(self, user_id: str) -> bool:
        """检查是否应该更新策略"""
        count = self._interaction_counts.get(user_id, 0)
        return count > 0 and count % self.strategy_update_interval == 0

    def update_strategy(self, user_id: str, conversation_history: List[Dict]):
        """
        更新 Agent 对用户的应对策略（MBTI维度微调）

        Args:
            user_id: 用户ID
            conversation_history: 对话历史
        """
        profile = self.get_or_create_profile(user_id)

        if not self.llm_client:
            return

        # 构建分析材料
        conv_text = "\n".join([
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
            for m in conversation_history[-20:]
        ])

        current_strategy = profile.agent_strategy
        personality = profile.personality

        prompt = f"""根据用户的对话表现，评估当前应对策略是否需要调整。

用户对话片段：
{conv_text}

用户已知特点：{personality.traits}
当前策略：{current_strategy}

请评估并输出 JSON：
{{
    "needs_adjustment": true或false,
    "new_strategy": {{
        "formality_level": 0.0-1.0,
        "proactivity": 0.0-1.0,
        "depth_preference": 0.0-1.0,
        "humor_level": 0.0-1.0
    }},
    "inferred_traits": ["用户性格特点，最多3个"],
    "adjustment_reason": "调整原因（如有）"
}}

策略说明：
- formality_level: 正式程度，0=很随意，1=很正式
- proactivity: 主动程度，0=被动回应，1=主动引导话题
- depth_preference: 深度偏好，0=浅层闲聊，1=深入讨论
- humor_level: 幽默程度，0=严肃，1=幽默"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_client.model if hasattr(self.llm_client, 'model') else "qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是一个对话策略优化专家。只输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)

            # 更新用户特点
            if result.get("inferred_traits"):
                for trait in result["inferred_traits"]:
                    if trait not in profile.personality.traits:
                        profile.personality.traits.append(trait)
                # 限制数量
                profile.personality.traits = profile.personality.traits[-10:]

            # 更新策略
            if result.get("needs_adjustment"):
                profile.agent_strategy = result.get("new_strategy", profile.agent_strategy)
                profile.last_strategy_update = datetime.now()
                profile.strategy_update_count += 1
                print(f"[UserProfile] 策略已更新: {result.get('adjustment_reason', '')}")

            # 重置计数
            self._interaction_counts[user_id] = 0

        except Exception as e:
            print(f"[UserProfile] 策略更新失败: {e}")

    def add_conversation_summary(
        self,
        user_id: str,
        session_id: str,
        conversation_history: List[Dict]
    ):
        """
        添加对话摘要

        应该在对话会话结束时调用
        """
        profile = self.get_or_create_profile(user_id)

        if not self.llm_client or not conversation_history:
            # 简单摘要
            if conversation_history:
                first_msg = conversation_history[0].get("content", "")[:50]
                summary = ConversationSummary(
                    session_id=session_id,
                    date=datetime.now(),
                    summary=f"讨论了: {first_msg}...",
                    key_topics=[],
                    sentiment="neutral"
                )
                profile.add_conversation_summary(summary)
            return

        # 构建对话文本
        conv_text = "\n".join([
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
            for m in conversation_history[-10:]
        ])

        prompt = f"""总结以下对话（1-2句话），并提取关键话题：

{conv_text}

输出 JSON 格式：
{{
    "summary": "对话摘要",
    "key_topics": ["话题1", "话题2"],
    "sentiment": "positive或negative或neutral"
}}"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_client.model if hasattr(self.llm_client, 'model') else "qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是一个对话分析助手。只输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)

            summary = ConversationSummary(
                session_id=session_id,
                date=datetime.now(),
                summary=result.get("summary", ""),
                key_topics=result.get("key_topics", []),
                sentiment=result.get("sentiment", "neutral")
            )

            profile.add_conversation_summary(summary)

        except Exception as e:
            print(f"[UserProfile] 对话摘要生成失败: {e}")

    def analyze_user_personality(self, user_id: str, conversation_history: List[Dict]):
        """
        分析用户个性（使用 LLM）

        这个方法调用成本较高，应该定期调用而非每次对话都调用
        """
        profile = self.get_or_create_profile(user_id)

        if not self.llm_client:
            return

        # 构建分析材料
        conv_text = "\n".join([
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
            for m in conversation_history[-30:]
        ])

        existing_traits = profile.personality.traits
        existing_interests = profile.personality.interests

        prompt = f"""根据以下对话，分析用户的性格特点：

{conv_text}

已知用户特点：{existing_traits}
已知用户兴趣：{existing_interests}

请分析并输出 JSON：
{{
    "inferred_mbti": "最可能的MBTI类型（如INTJ）或null",
    "mbti_confidence": 0.0-1.0的置信度,
    "traits": ["性格特点列表，最多5个"],
    "communication_preferences": {{
        "preferred_response_length": "short或medium或long",
        "likes_questions": "yes或no或unknown",
        "prefers_formal": "yes或no或unknown",
        "enjoys_humor": "yes或no或unknown"
    }},
    "interests": ["兴趣爱好列表，最多5个"]
}}"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_client.model if hasattr(self.llm_client, 'model') else "qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是一个用户行为分析专家。只输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)

            profile.personality.inferred_mbti = result.get("inferred_mbti")
            profile.personality.mbti_confidence = result.get("mbti_confidence", 0.0)
            profile.personality.traits = result.get("traits", [])
            profile.personality.communication_preferences = result.get("communication_preferences", {})
            profile.personality.interests = result.get("interests", [])

        except Exception as e:
            print(f"[UserProfile] 个性分析失败: {e}")

    def save_profile(self, user_id: str):
        """保存用户画像"""
        profile = self._profiles.get(user_id)
        if not profile:
            return

        os.makedirs(self.profile_dir, exist_ok=True)
        profile_file = os.path.join(self.profile_dir, f"{user_id}_profile.json")

        data = profile.to_dict()

        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_all_profiles(self):
        """保存所有用户画像"""
        for user_id in self._profiles:
            self.save_profile(user_id)

    def generate_profile_context(self, user_id: str) -> str:
        """生成用户画像的上下文字符串"""
        profile = self.get_or_create_profile(user_id)
        return profile.to_context_string()
