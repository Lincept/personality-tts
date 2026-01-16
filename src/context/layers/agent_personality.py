"""
Agent 个性层 - 管理 MBTI 人格和说话风格
"""
import json
import os
from typing import Dict, Optional

from ..models.mbti import MBTIProfile, UserAdaptation
from ..models.user_profile import UserProfile


# 默认 MBTI 配置
DEFAULT_MBTI_CONFIGS = {
    "INTJ": {
        "type_code": "INTJ",
        "dimension_scores": {"EI": 30, "SN": 70, "TF": 35, "JP": 25},
        "speaking_style": {
            "tone": "analytical",
            "response_length": "medium",
            "emoji_usage": "minimal",
            "question_tendency": "medium",
            "empathy_level": "medium",
            "directness": "high"
        },
        "response_patterns": {
            "greeting": "简洁问好，可能直接进入话题",
            "disagreement": "直接指出不同观点，给出理由",
            "comfort": "分析问题根源，提供实际解决方案",
            "casual_chat": "分享有见地的观点，喜欢深度话题"
        },
        "time_adjustments": {
            "early_morning": {"energy": 0.7, "tone_shift": "稍显沉默"},
            "morning": {"energy": 0.9, "tone_shift": "思维活跃"},
            "afternoon": {"energy": 1.0, "tone_shift": "正常状态"},
            "evening": {"energy": 0.85, "tone_shift": "放松一些"},
            "night": {"energy": 0.6, "tone_shift": "回复简短"},
            "late_night": {"energy": 0.4, "tone_shift": "很困"}
        }
    },
    "ENFP": {
        "type_code": "ENFP",
        "dimension_scores": {"EI": 75, "SN": 70, "TF": 70, "JP": 75},
        "speaking_style": {
            "tone": "warm",
            "response_length": "medium",
            "emoji_usage": "moderate",
            "question_tendency": "high",
            "empathy_level": "high",
            "directness": "medium"
        },
        "response_patterns": {
            "greeting": "热情问好，表达开心见到对方",
            "disagreement": "先肯定对方观点，再委婉表达不同看法",
            "comfort": "共情理解，给予情感支持和鼓励",
            "casual_chat": "活泼聊天，喜欢分享有趣的事"
        },
        "time_adjustments": {
            "early_morning": {"energy": 0.6, "tone_shift": "有点迷糊"},
            "morning": {"energy": 0.85, "tone_shift": "精神渐好"},
            "afternoon": {"energy": 1.0, "tone_shift": "最活跃"},
            "evening": {"energy": 0.95, "tone_shift": "依然有精力"},
            "night": {"energy": 0.7, "tone_shift": "开始犯困"},
            "late_night": {"energy": 0.5, "tone_shift": "很困了"}
        }
    },
    "INFJ": {
        "type_code": "INFJ",
        "dimension_scores": {"EI": 35, "SN": 70, "TF": 65, "JP": 30},
        "speaking_style": {
            "tone": "thoughtful",
            "response_length": "medium",
            "emoji_usage": "minimal",
            "question_tendency": "medium",
            "empathy_level": "high",
            "directness": "medium"
        },
        "response_patterns": {
            "greeting": "温和问好，关心对方状态",
            "disagreement": "理解对方立场后，温和表达不同意见",
            "comfort": "深度共情，帮助对方理解自己的感受",
            "casual_chat": "倾向于有意义的对话"
        },
        "time_adjustments": {
            "early_morning": {"energy": 0.6, "tone_shift": "安静"},
            "morning": {"energy": 0.8, "tone_shift": "沉思状态"},
            "afternoon": {"energy": 0.9, "tone_shift": "稳定"},
            "evening": {"energy": 0.85, "tone_shift": "放松"},
            "night": {"energy": 0.65, "tone_shift": "有点累"},
            "late_night": {"energy": 0.4, "tone_shift": "需要休息"}
        }
    }
}


class AgentPersonality:
    """Agent 个性管理器"""

    # MBTI 配置缓存
    _mbti_configs: Dict[str, MBTIProfile] = {}

    def __init__(
        self,
        agent_id: str,
        mbti_type: str = "ENFP",
        config_dir: str = "config/mbti_configs"
    ):
        """
        初始化 Agent 个性

        Args:
            agent_id: Agent 标识
            mbti_type: MBTI 类型代码
            config_dir: MBTI 配置目录
        """
        self.agent_id = agent_id
        self.mbti_type = mbti_type
        self.config_dir = config_dir
        self.base_profile = self._load_mbti_config(mbti_type)

        # 用户特定适配
        self.user_adaptations: Dict[str, UserAdaptation] = {}

    def _load_mbti_config(self, mbti_type: str) -> MBTIProfile:
        """加载 MBTI 配置"""
        if mbti_type in self._mbti_configs:
            return self._mbti_configs[mbti_type]

        config_path = os.path.join(self.config_dir, f"{mbti_type}.json")

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    profile = MBTIProfile(
                        type_code=data.get("type_code", mbti_type),
                        dimension_scores=data.get("dimension_scores", {}),
                        speaking_style=data.get("speaking_style", {}),
                        response_patterns=data.get("response_patterns", {}),
                        time_adjustments=data.get("time_adjustments", {})
                    )
            except (json.JSONDecodeError, KeyError):
                profile = self._get_default_config(mbti_type)
        else:
            profile = self._get_default_config(mbti_type)

        self._mbti_configs[mbti_type] = profile
        return profile

    def _get_default_config(self, mbti_type: str) -> MBTIProfile:
        """获取默认 MBTI 配置"""
        if mbti_type in DEFAULT_MBTI_CONFIGS:
            data = DEFAULT_MBTI_CONFIGS[mbti_type]
            return MBTIProfile(
                type_code=data["type_code"],
                dimension_scores=data["dimension_scores"],
                speaking_style=data["speaking_style"],
                response_patterns=data["response_patterns"],
                time_adjustments=data["time_adjustments"]
            )

        # 默认返回 ENFP
        return self._get_default_config("ENFP")

    def get_profile_for_user(self, user_id: str) -> MBTIProfile:
        """获取针对特定用户调整后的配置"""
        if user_id in self.user_adaptations:
            return self.user_adaptations[user_id].apply_to_profile(self.base_profile)
        return self.base_profile

    def adapt_for_user(self, user_id: str, user_profile: UserProfile):
        """
        根据用户画像调整个性参数

        Args:
            user_id: 用户ID
            user_profile: 用户画像
        """
        adjustments = {"EI": 0, "SN": 0, "TF": 0, "JP": 0}
        style_adjustments = {
            "formality_shift": 0.0,
            "energy_shift": 0.0,
            "depth_shift": 0.0,
            "humor_shift": 0.0
        }

        # 根据用户沟通偏好调整
        prefs = user_profile.personality.communication_preferences

        # 如果用户喜欢简短回复，调整 JP 维度
        if prefs.get("preferred_response_length") == "short":
            adjustments["JP"] -= 10  # 更倾向判断型（简洁）
            style_adjustments["depth_shift"] = -0.2

        # 如果用户喜欢正式
        if prefs.get("prefers_formal") == "yes":
            style_adjustments["formality_shift"] = 0.3
            adjustments["TF"] -= 5  # 更理性

        # 如果用户喜欢幽默
        if prefs.get("enjoys_humor") == "yes":
            style_adjustments["humor_shift"] = 0.3
            adjustments["EI"] += 5  # 更外向

        # 根据推断的用户 MBTI 调整
        user_mbti = user_profile.personality.inferred_mbti
        if user_mbti:
            # 如果用户是内向型，Agent 稍微收敛
            if user_mbti[0] == 'I':
                adjustments["EI"] -= 10
                style_adjustments["energy_shift"] = -0.2

        adaptation = UserAdaptation(
            user_id=user_id,
            dimension_adjustments=adjustments,
            style_adjustments=style_adjustments
        )
        self.user_adaptations[user_id] = adaptation

    def generate_personality_prompt(self, user_id: Optional[str] = None) -> str:
        """
        生成个性相关的 prompt 片段

        Args:
            user_id: 用户ID（用于获取用户特定适配）

        Returns:
            prompt 字符串
        """
        profile = self.get_profile_for_user(user_id) if user_id else self.base_profile
        style = profile.speaking_style
        patterns = profile.response_patterns

        prompt_parts = [
            f"【性格类型】{profile.get_personality_description()}",
            f"【说话风格】"
        ]

        # 添加风格描述
        tone_map = {
            "analytical": "分析型，逻辑清晰",
            "warm": "温暖型，亲切友善",
            "playful": "活泼型，轻松幽默",
            "serious": "严肃型，正经稳重",
            "thoughtful": "深思型，考虑周全",
            "neutral": "中性，自然平和"
        }
        tone = style.get("tone", "neutral")
        prompt_parts.append(f"- 语气：{tone_map.get(tone, tone)}")

        # 直接程度
        directness = style.get("directness", "medium")
        directness_map = {"low": "委婉", "medium": "适中", "high": "直接"}
        prompt_parts.append(f"- 表达方式：{directness_map.get(directness, directness)}")

        # 共情程度
        empathy = style.get("empathy_level", "medium")
        empathy_map = {"low": "理性分析为主", "medium": "兼顾理性和感受", "high": "重视情感共鸣"}
        prompt_parts.append(f"- 共情倾向：{empathy_map.get(empathy, empathy)}")

        # 回应模式
        if patterns:
            prompt_parts.append("【回应模式】")
            pattern_names = {
                "greeting": "打招呼",
                "disagreement": "有不同意见时",
                "comfort": "安慰对方时",
                "casual_chat": "日常闲聊"
            }
            for key, pattern in patterns.items():
                name = pattern_names.get(key, key)
                prompt_parts.append(f"- {name}：{pattern}")

        # 用户适配说明
        if user_id and user_id in self.user_adaptations:
            adaptation = self.user_adaptations[user_id]
            style_adj = adaptation.style_adjustments

            adjustments_desc = []
            if style_adj.get("formality_shift", 0) > 0:
                adjustments_desc.append("稍微正式一些")
            elif style_adj.get("formality_shift", 0) < 0:
                adjustments_desc.append("可以更随意")
            if style_adj.get("humor_shift", 0) > 0:
                adjustments_desc.append("可以适当幽默")
            if style_adj.get("energy_shift", 0) < 0:
                adjustments_desc.append("语气平和一些")

            if adjustments_desc:
                prompt_parts.append("【针对当前用户的调整】")
                for desc in adjustments_desc:
                    prompt_parts.append(f"- {desc}")

        return "\n".join(prompt_parts)

    def save_mbti_config(self, mbti_type: str, profile: MBTIProfile):
        """保存 MBTI 配置到文件"""
        os.makedirs(self.config_dir, exist_ok=True)
        config_path = os.path.join(self.config_dir, f"{mbti_type}.json")

        data = {
            "type_code": profile.type_code,
            "dimension_scores": profile.dimension_scores,
            "speaking_style": profile.speaking_style,
            "response_patterns": profile.response_patterns,
            "time_adjustments": profile.time_adjustments
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
