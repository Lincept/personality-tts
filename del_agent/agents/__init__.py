"""
Agents module for AI Data Factory
Contains various AI agents for data processing
"""

# 导出前端相关的 Agent，避免循环导入问题
try:
    from .critic import CriticAgent
    from .persona import PersonaAgent
    from .info_extractor import InfoExtractorAgent, InfoExtractionHelper
except (ImportError, ValueError):
    from agents.critic import CriticAgent
    from agents.persona import PersonaAgent
    from agents.info_extractor import InfoExtractorAgent, InfoExtractionHelper

__all__ = ["CriticAgent", "PersonaAgent", "InfoExtractorAgent", "InfoExtractionHelper"]