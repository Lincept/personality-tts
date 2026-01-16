"""
事件模型
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict
from enum import Enum


class EventType(Enum):
    """事件类型"""
    CONVERSATION = "conversation"      # 对话事件
    LEARNING = "learning"              # 学习到新信息
    EMOTIONAL = "emotional"            # 情感类事件
    TASK = "task"                      # 任务类事件
    MILESTONE = "milestone"            # 里程碑事件

    @classmethod
    def from_string(cls, s: str) -> 'EventType':
        """从字符串转换"""
        mapping = {
            "conversation": cls.CONVERSATION,
            "learning": cls.LEARNING,
            "emotional": cls.EMOTIONAL,
            "task": cls.TASK,
            "milestone": cls.MILESTONE
        }
        return mapping.get(s.lower(), cls.CONVERSATION)


@dataclass
class Event:
    """单个事件"""
    event_id: str
    event_type: EventType
    content: str                       # 事件描述
    timestamp: datetime
    participants: List[str] = field(default_factory=list)  # 涉及的用户/实体
    importance: float = 0.5            # 重要程度 0-1

    # 元数据（用于检索）
    tags: List[str] = field(default_factory=list)
    context: Dict[str, str] = field(default_factory=dict)

    def to_mem0_format(self) -> str:
        """转换为 Mem0 存储格式"""
        date_str = self.timestamp.strftime('%Y-%m-%d')
        return f"[{date_str}] {self.content}"

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "participants": self.participants,
            "importance": self.importance,
            "tags": self.tags,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """从字典恢复"""
        return cls(
            event_id=data["event_id"],
            event_type=EventType.from_string(data.get("event_type", "conversation")),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            participants=data.get("participants", []),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            context=data.get("context", {})
        )


@dataclass
class DailySummary:
    """每日活动摘要"""
    date: date
    agent_id: str

    # 摘要文本（默认注入上下文）
    summary_text: str = ""

    # 关键事件列表
    key_events: List[Event] = field(default_factory=list)

    # 统计信息
    total_conversations: int = 0
    total_messages: int = 0
    unique_users: List[str] = field(default_factory=list)

    # 情感基调
    overall_mood: str = "neutral"     # positive/negative/neutral

    def to_context_string(self) -> str:
        """生成上下文注入字符串"""
        if not self.summary_text:
            return "（今天还没有什么特别的事情）"
        return f"【最近动态】\n{self.summary_text}"

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "date": self.date.isoformat(),
            "agent_id": self.agent_id,
            "summary_text": self.summary_text,
            "key_events": [e.to_dict() for e in self.key_events],
            "total_conversations": self.total_conversations,
            "total_messages": self.total_messages,
            "unique_users": self.unique_users,
            "overall_mood": self.overall_mood
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DailySummary':
        """从字典恢复"""
        key_events = [Event.from_dict(e) for e in data.get("key_events", [])]
        return cls(
            date=date.fromisoformat(data["date"]),
            agent_id=data["agent_id"],
            summary_text=data.get("summary_text", ""),
            key_events=key_events,
            total_conversations=data.get("total_conversations", 0),
            total_messages=data.get("total_messages", 0),
            unique_users=data.get("unique_users", []),
            overall_mood=data.get("overall_mood", "neutral")
        )


@dataclass
class EventQuery:
    """事件查询参数"""
    user_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    event_types: List[EventType] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    limit: int = 10
