"""
Agent 状态模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TimeOfDay(Enum):
    """时间段枚举"""
    EARLY_MORNING = "early_morning"  # 5:00-8:00
    MORNING = "morning"              # 8:00-12:00
    AFTERNOON = "afternoon"          # 12:00-18:00
    EVENING = "evening"              # 18:00-22:00
    NIGHT = "night"                  # 22:00-24:00
    LATE_NIGHT = "late_night"        # 0:00-5:00

    @classmethod
    def from_hour(cls, hour: int) -> 'TimeOfDay':
        """根据小时获取时间段"""
        if 5 <= hour < 8:
            return cls.EARLY_MORNING
        elif 8 <= hour < 12:
            return cls.MORNING
        elif 12 <= hour < 18:
            return cls.AFTERNOON
        elif 18 <= hour < 22:
            return cls.EVENING
        elif 22 <= hour < 24:
            return cls.NIGHT
        else:
            return cls.LATE_NIGHT

    def get_description(self) -> str:
        """获取时间段描述"""
        mapping = {
            TimeOfDay.EARLY_MORNING: "清晨",
            TimeOfDay.MORNING: "上午",
            TimeOfDay.AFTERNOON: "下午",
            TimeOfDay.EVENING: "傍晚",
            TimeOfDay.NIGHT: "夜晚",
            TimeOfDay.LATE_NIGHT: "深夜"
        }
        return mapping.get(self, "")


@dataclass
class FatigueState:
    """疲劳状态"""
    level: float = 0.0              # 0.0-1.0, 0表示精力充沛
    session_start: Optional[datetime] = None
    total_messages: int = 0

    # 疲劳阈值配置
    fatigue_rate: float = 0.02      # 每条消息增加的疲劳度
    recovery_rate: float = 0.1      # 每小时恢复的疲劳度
    max_fatigue: float = 0.8        # 最大疲劳度

    def update_on_message(self):
        """每次消息后更新疲劳度"""
        self.total_messages += 1
        self.level = min(self.max_fatigue, self.level + self.fatigue_rate)

    def recover(self, hours_passed: float):
        """根据休息时间恢复"""
        recovery = hours_passed * self.recovery_rate
        self.level = max(0.0, self.level - recovery)

    def get_fatigue_descriptor(self) -> str:
        """获取疲劳状态描述"""
        if self.level < 0.2:
            return "精力充沛"
        elif self.level < 0.4:
            return "状态良好"
        elif self.level < 0.6:
            return "稍显疲惫"
        elif self.level < 0.8:
            return "比较累了"
        else:
            return "非常疲惫"

    def get_response_modifiers(self) -> dict:
        """获取影响回复的参数"""
        return {
            "length_factor": 1.0 - self.level * 0.3,   # 疲劳越高回复越短
            "energy_factor": 1.0 - self.level * 0.4,   # 疲劳越高活力越低
            "patience_factor": 1.0 - self.level * 0.2  # 疲劳越高耐心越少
        }


@dataclass
class AgentStateModel:
    """Agent 完整状态"""
    agent_id: str

    # 时间感知
    current_time: datetime = field(default_factory=datetime.now)
    time_of_day: TimeOfDay = TimeOfDay.AFTERNOON

    # 疲劳状态
    fatigue: FatigueState = field(default_factory=FatigueState)

    # 会话状态
    session_id: Optional[str] = None
    last_interaction: Optional[datetime] = None
    conversation_count: int = 0  # 当前会话的对话计数

    # 状态修饰词（用于 prompt 注入）
    mood_modifiers: List[str] = field(default_factory=list)
    # 如: ["有点困", "心情不错", "想聊天"]

    def update_time(self):
        """更新时间感知"""
        self.current_time = datetime.now()
        self.time_of_day = TimeOfDay.from_hour(self.current_time.hour)

    def get_time_based_mood(self) -> List[str]:
        """根据时间获取心情修饰词"""
        moods = {
            TimeOfDay.EARLY_MORNING: ["刚醒", "有点迷糊"],
            TimeOfDay.MORNING: ["精神不错", "适合聊天"],
            TimeOfDay.AFTERNOON: ["状态稳定"],
            TimeOfDay.EVENING: ["放松状态", "可以随意聊"],
            TimeOfDay.NIGHT: ["有点困了", "想休息"],
            TimeOfDay.LATE_NIGHT: ["很困", "回复会简短"]
        }
        return moods.get(self.time_of_day, [])

    def to_context_string(self) -> str:
        """生成上下文注入字符串"""
        time_desc = self.time_of_day.get_description()
        fatigue_desc = self.fatigue.get_fatigue_descriptor()

        # 合并时间心情和疲劳心情
        all_moods = list(set(self.mood_modifiers + self.get_time_based_mood()))
        if self.fatigue.level > 0.5:
            all_moods.append("有点累了")
        mood_str = "、".join(all_moods) if all_moods else "正常"

        return f"""【当前状态】
- 时间：{self.current_time.strftime('%H:%M')}（{time_desc}）
- 精力：{fatigue_desc}
- 状态：{mood_str}"""

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "agent_id": self.agent_id,
            "fatigue_level": self.fatigue.level,
            "total_messages": self.fatigue.total_messages,
            "conversation_count": self.conversation_count,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None
        }

    @classmethod
    def from_dict(cls, data: dict, agent_id: str) -> 'AgentStateModel':
        """从字典恢复状态"""
        fatigue = FatigueState(
            level=data.get("fatigue_level", 0.0),
            total_messages=data.get("total_messages", 0)
        )

        last_interaction = None
        if data.get("last_interaction"):
            last_interaction = datetime.fromisoformat(data["last_interaction"])

        state = cls(
            agent_id=agent_id,
            fatigue=fatigue,
            last_interaction=last_interaction,
            conversation_count=data.get("conversation_count", 0)
        )
        state.update_time()
        return state
