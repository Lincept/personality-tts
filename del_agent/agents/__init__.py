"""
Agents module for AI Data Factory
Contains various AI agents for data processing
"""

# 暂时只导出 CriticAgent，避免循环导入问题
try:
    from .critic import CriticAgent
except (ImportError, ValueError):
    from agents.critic import CriticAgent

__all__ = ["CriticAgent"]