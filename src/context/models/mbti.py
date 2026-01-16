"""
MBTI 人格模型
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class MBTIDimension(Enum):
    """MBTI 四个维度"""
    EI = "EI"  # 外向(E)-内向(I)
    SN = "SN"  # 感觉(S)-直觉(N)
    TF = "TF"  # 思考(T)-情感(F)
    JP = "JP"  # 判断(J)-感知(P)


@dataclass
class MBTIProfile:
    """MBTI 人格配置"""
    type_code: str  # 如 "INTJ", "ENFP"

    # 维度得分 (0-100, 50为中点)
    # <50 偏向第一个字母, >50 偏向第二个字母
    dimension_scores: Dict[str, int] = field(default_factory=lambda: {
        "EI": 50,  # <50 内向(I), >50 外向(E)
        "SN": 50,  # <50 感觉(S), >50 直觉(N)
        "TF": 50,  # <50 思考(T), >50 情感(F)
        "JP": 50   # <50 判断(J), >50 感知(P)
    })

    # 说话风格配置
    speaking_style: Dict[str, str] = field(default_factory=lambda: {
        "tone": "neutral",           # 语气：analytical/warm/playful/serious/neutral
        "response_length": "medium", # 回复长度：short/medium/long
        "emoji_usage": "minimal",    # emoji使用：none/minimal/moderate/frequent
        "question_tendency": "medium", # 提问倾向：low/medium/high
        "empathy_level": "medium",   # 共情程度：low/medium/high
        "directness": "medium"       # 直接程度：low/medium/high
    })

    # 回应模式配置
    response_patterns: Dict[str, str] = field(default_factory=dict)
    # 示例:
    # {
    #   "greeting": "简洁问好",
    #   "disagreement": "直接表达不同看法",
    #   "comfort": "分析问题提供方案",
    #   "casual_chat": "分享有见地的观点"
    # }

    # 时间段行为调整
    time_adjustments: Dict[str, Dict] = field(default_factory=dict)
    # 示例:
    # {
    #   "morning": {"energy": 0.8, "tone_shift": "稍显慵懒"},
    #   "night": {"energy": 0.6, "tone_shift": "困倦简短"}
    # }

    def get_dimension_tendency(self, dimension: str) -> str:
        """获取维度倾向描述"""
        score = self.dimension_scores.get(dimension, 50)
        if dimension == "EI":
            return "外向" if score > 50 else "内向"
        elif dimension == "SN":
            return "直觉" if score > 50 else "感觉"
        elif dimension == "TF":
            return "情感" if score > 50 else "思考"
        elif dimension == "JP":
            return "感知" if score > 50 else "判断"
        return ""

    def get_personality_description(self) -> str:
        """生成人格描述"""
        tendencies = [
            self.get_dimension_tendency("EI"),
            self.get_dimension_tendency("SN"),
            self.get_dimension_tendency("TF"),
            self.get_dimension_tendency("JP")
        ]
        return f"{self.type_code} ({'/'.join(tendencies)})"


@dataclass
class UserAdaptation:
    """针对特定用户的 MBTI 微调"""
    user_id: str

    # 各维度调整值 (-15 ~ +15)
    dimension_adjustments: Dict[str, int] = field(default_factory=lambda: {
        "EI": 0,
        "SN": 0,
        "TF": 0,
        "JP": 0
    })
    # 例: {"EI": -10, "TF": +5} 表示对该用户更内敛、更有情感

    # 风格调整
    style_adjustments: Dict[str, float] = field(default_factory=lambda: {
        "formality_shift": 0.0,    # -1.0 更随意, +1.0 更正式
        "energy_shift": 0.0,       # -1.0 更安静, +1.0 更活跃
        "depth_shift": 0.0,        # -1.0 更浅层, +1.0 更深入
        "humor_shift": 0.0         # -1.0 更严肃, +1.0 更幽默
    })

    # 调整原因记录
    adjustment_reason: Optional[str] = None

    def apply_to_profile(self, base_profile: MBTIProfile) -> MBTIProfile:
        """将微调应用到基础配置"""
        adjusted_scores = {}
        for dim, base_score in base_profile.dimension_scores.items():
            adjustment = self.dimension_adjustments.get(dim, 0)
            # 限制在 0-100 范围内
            adjusted_scores[dim] = max(0, min(100, base_score + adjustment))

        return MBTIProfile(
            type_code=base_profile.type_code,
            dimension_scores=adjusted_scores,
            speaking_style=base_profile.speaking_style.copy(),
            response_patterns=base_profile.response_patterns.copy(),
            time_adjustments=base_profile.time_adjustments.copy()
        )
