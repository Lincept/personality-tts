"""
AI Data Factory - 轻量级AI数据工厂框架
主模块初始化文件
"""

from .core import LLMProvider, OpenAICompatibleProvider
# 暂时注释掉 RawCommentCleaner 导入，避免循环导入
# from .agents import RawCommentCleaner
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
    # "RawCommentCleaner",  # 暂时注释，避免循环导入
    
    # Models
    "CommentCleaningResult",
    "ProcessingStats", 
    "LLMConfig",
    "AgentConfig",
    
    # Utils
    "ConfigManager",
    "get_config_manager",
]