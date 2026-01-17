"""
AI Data Factory - 轻量级AI数据工厂框架
主模块初始化文件
"""

from .core import LLMProvider, OpenAICompatibleProvider
from .agents import RawCommentCleaner
from .models import CommentCleaningResult, ProcessingStats, LLMConfig, AgentConfig
from .utils import ConfigManager, get_config_manager
from .core.prompt_manager import PromptManager, get_default_prompt_manager

__version__ = "0.1.0"
__author__ = "AI Data Factory Team"

__all__ = [
    # Core components
    "LLMProvider",
    "OpenAICompatibleProvider", 
    "PromptManager",
    "get_default_prompt_manager",
    
    # Agents
    "RawCommentCleaner",
    
    # Models
    "CommentCleaningResult",
    "ProcessingStats", 
    "LLMConfig",
    "AgentConfig",
    
    # Utils
    "ConfigManager",
    "get_config_manager",
]