"""
Agent 状态层 - 管理时间感知和疲劳状态
"""
import json
import os
from datetime import datetime
from typing import Optional

from ..models.state import AgentStateModel, FatigueState, TimeOfDay


class AgentState:
    """Agent 状态管理器"""

    def __init__(self, agent_id: str, state_dir: str = "data/context/agent_state"):
        """
        初始化状态管理器

        Args:
            agent_id: Agent 标识
            state_dir: 状态存储目录
        """
        self.agent_id = agent_id
        self.state_dir = state_dir
        self.state = self._load_or_create_state()

    def _load_or_create_state(self) -> AgentStateModel:
        """加载或创建状态"""
        state_file = os.path.join(self.state_dir, f"{self.agent_id}_state.json")

        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 计算离线期间的恢复
                last_time_str = data.get("last_interaction")
                if last_time_str:
                    last_time = datetime.fromisoformat(last_time_str)
                    hours_passed = (datetime.now() - last_time).total_seconds() / 3600

                    fatigue = FatigueState(
                        level=data.get("fatigue_level", 0.0),
                        total_messages=data.get("total_messages", 0)
                    )
                    # 应用恢复
                    fatigue.recover(hours_passed)

                    state = AgentStateModel(
                        agent_id=self.agent_id,
                        fatigue=fatigue,
                        last_interaction=last_time,
                        conversation_count=data.get("conversation_count", 0)
                    )
                else:
                    state = AgentStateModel(agent_id=self.agent_id)

            except (json.JSONDecodeError, KeyError):
                state = AgentStateModel(agent_id=self.agent_id)
        else:
            state = AgentStateModel(agent_id=self.agent_id)

        # 更新时间感知
        self._update_time_awareness(state)
        return state

    def _update_time_awareness(self, state: AgentStateModel):
        """更新时间感知"""
        now = datetime.now()
        state.current_time = now
        state.time_of_day = TimeOfDay.from_hour(now.hour)

        # 根据时间设置心情修饰词
        state.mood_modifiers = state.get_time_based_mood()

    def on_message(self):
        """处理消息时更新状态"""
        self.state.fatigue.update_on_message()
        self.state.last_interaction = datetime.now()
        self.state.conversation_count += 1
        self._update_time_awareness(self.state)

        # 根据疲劳度更新心情修饰
        if self.state.fatigue.level > 0.6:
            if "有点累了" not in self.state.mood_modifiers:
                self.state.mood_modifiers.append("有点累了")

    def reset_session(self):
        """重置会话（新对话开始时调用）"""
        self.state.conversation_count = 0
        self.state.fatigue.session_start = datetime.now()

    def save_state(self):
        """保存状态到文件"""
        os.makedirs(self.state_dir, exist_ok=True)
        state_file = os.path.join(self.state_dir, f"{self.agent_id}_state.json")

        data = self.state.to_dict()

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generate_state_prompt(self) -> str:
        """
        生成状态相关的 prompt 片段

        Returns:
            prompt 字符串
        """
        return self.state.to_context_string()

    def get_response_style_modifiers(self) -> dict:
        """
        获取影响回复风格的参数

        Returns:
            风格修饰参数
        """
        modifiers = self.state.fatigue.get_response_modifiers()

        # 时间影响
        if self.state.time_of_day in [TimeOfDay.NIGHT, TimeOfDay.LATE_NIGHT]:
            modifiers["length_factor"] -= 0.2
            modifiers["energy_factor"] -= 0.3

        return modifiers

    def should_trigger_batch_processing(self, interval: int = 5) -> bool:
        """
        检查是否应该触发批量处理

        Args:
            interval: 触发间隔（对话次数）

        Returns:
            是否应该触发
        """
        return self.state.conversation_count > 0 and self.state.conversation_count % interval == 0
