"""
Backend Package
后端数据工厂模块
"""

try:
    from .factory import DataFactoryPipeline
except ImportError:
    from del_agent.backend.factory import DataFactoryPipeline

__all__ = ["DataFactoryPipeline"]
