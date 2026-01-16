"""
动态上下文注入系统

提供分层的上下文管理：
- Agent 个性层 (MBTI)
- 状态层 (时间感知/疲劳度)
- 事件层 (活动摘要/事件存储)
- 用户画像层 (用户个性/策略调整)
"""

from .context_builder import ContextBuilder

__all__ = ['ContextBuilder']
