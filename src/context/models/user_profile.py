"""
用户画像模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class UserPersonality:
    """用户个性分析"""
    # 推测的 MBTI（用于调整 Agent 应对策略）
    inferred_mbti: Optional[str] = None
    mbti_confidence: float = 0.0      # 置信度 0-1

    # 性格特点标签
    traits: List[str] = field(default_factory=list)
    # 如: ["健谈", "好奇心强", "偏理性", "喜欢深度讨论"]

    # 沟通偏好
    communication_preferences: Dict[str, str] = field(default_factory=lambda: {
        "preferred_response_length": "medium",  # short/medium/long
        "likes_questions": "unknown",           # yes/no/unknown
        "prefers_formal": "unknown",            # yes/no/unknown
        "enjoys_humor": "unknown"               # yes/no/unknown
    })

    # 兴趣领域
    interests: List[str] = field(default_factory=list)

    # 敏感话题（需要谨慎处理）
    sensitive_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "inferred_mbti": self.inferred_mbti,
            "mbti_confidence": self.mbti_confidence,
            "traits": self.traits,
            "communication_preferences": self.communication_preferences,
            "interests": self.interests,
            "sensitive_topics": self.sensitive_topics
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UserPersonality':
        """从字典恢复"""
        return cls(
            inferred_mbti=data.get("inferred_mbti"),
            mbti_confidence=data.get("mbti_confidence", 0.0),
            traits=data.get("traits", []),
            communication_preferences=data.get("communication_preferences", {}),
            interests=data.get("interests", []),
            sensitive_topics=data.get("sensitive_topics", [])
        )


@dataclass
class ConversationSummary:
    """对话摘要"""
    session_id: str
    date: datetime
    summary: str                      # 对话主要内容概述
    key_topics: List[str] = field(default_factory=list)
    sentiment: str = "neutral"        # positive/negative/neutral
    notable_moments: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "session_id": self.session_id,
            "date": self.date.isoformat(),
            "summary": self.summary,
            "key_topics": self.key_topics,
            "sentiment": self.sentiment,
            "notable_moments": self.notable_moments
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationSummary':
        """从字典恢复"""
        return cls(
            session_id=data.get("session_id", ""),
            date=datetime.fromisoformat(data["date"]),
            summary=data.get("summary", ""),
            key_topics=data.get("key_topics", []),
            sentiment=data.get("sentiment", "neutral"),
            notable_moments=data.get("notable_moments", [])
        )


@dataclass
class UserProfile:
    """完整用户画像"""
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 用户个性
    personality: UserPersonality = field(default_factory=UserPersonality)

    # 最近对话摘要（保留最近5次）
    recent_conversations: List[ConversationSummary] = field(default_factory=list)

    # Agent 对该用户的应对策略
    agent_strategy: Dict[str, float] = field(default_factory=lambda: {
        "formality_level": 0.5,       # 0-1, 正式程度
        "proactivity": 0.5,           # 0-1, 主动程度
        "depth_preference": 0.5,      # 0-1, 深度偏好
        "humor_level": 0.5            # 0-1, 幽默程度
    })

    # 上次策略调整时间
    last_strategy_update: Optional[datetime] = None
    strategy_update_count: int = 0

    # 交互统计
    total_interactions: int = 0

    def to_context_string(self) -> str:
        """生成上下文注入字符串"""
        parts = [f"【用户画像：{self.user_id}】"]

        if self.personality.traits:
            parts.append(f"- 性格特点：{'、'.join(self.personality.traits[:5])}")

        if self.personality.interests:
            parts.append(f"- 兴趣爱好：{'、'.join(self.personality.interests[:5])}")

        if self.recent_conversations:
            recent = self.recent_conversations[-1]
            parts.append(f"- 上次聊天：{recent.summary[:50]}...")

        return "\n".join(parts)

    def get_recent_summaries(self, count: int = 3) -> str:
        """获取最近几次对话摘要"""
        if not self.recent_conversations:
            return "（暂无历史对话记录）"

        summaries = []
        for conv in self.recent_conversations[-count:]:
            summaries.append(f"- {conv.date.strftime('%m/%d')}: {conv.summary}")

        return "\n".join(summaries)

    def add_conversation_summary(self, summary: ConversationSummary):
        """添加对话摘要（自动限制数量）"""
        self.recent_conversations.append(summary)
        if len(self.recent_conversations) > 5:
            self.recent_conversations = self.recent_conversations[-5:]
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "personality": self.personality.to_dict(),
            "recent_conversations": [c.to_dict() for c in self.recent_conversations],
            "agent_strategy": self.agent_strategy,
            "last_strategy_update": self.last_strategy_update.isoformat() if self.last_strategy_update else None,
            "strategy_update_count": self.strategy_update_count,
            "total_interactions": self.total_interactions
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UserProfile':
        """从字典恢复"""
        personality = UserPersonality.from_dict(data.get("personality", {}))
        conversations = [ConversationSummary.from_dict(c) for c in data.get("recent_conversations", [])]

        last_update = None
        if data.get("last_strategy_update"):
            last_update = datetime.fromisoformat(data["last_strategy_update"])

        return cls(
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            personality=personality,
            recent_conversations=conversations,
            agent_strategy=data.get("agent_strategy", {}),
            last_strategy_update=last_update,
            strategy_update_count=data.get("strategy_update_count", 0),
            total_interactions=data.get("total_interactions", 0)
        )
