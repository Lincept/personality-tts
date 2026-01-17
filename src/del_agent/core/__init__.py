"""
Core module for AI Data Factory
Contains LLM adapters and base functionality
"""

from .llm_adapter import LLMProvider, OpenAICompatibleProvider

__all__ = ["LLMProvider", "OpenAICompatibleProvider"]