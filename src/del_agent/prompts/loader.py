"""
Prompt loader utility
辅助加载提示词模板的工具类
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import json

from ..core.prompt_manager import PromptManager, PromptTemplate


class PromptLoader:
    """
    提示词加载器
    提供便捷的提示词模板加载功能
    """
    
    @staticmethod
    def load_from_yaml(file_path: str) -> PromptTemplate:
        """
        从YAML文件加载提示词模板
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            提示词模板对象
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return PromptTemplate(
            name=data['name'],
            system_prompt=data['system_prompt'],
            user_prompt=data.get('user_prompt', '')
        )
    
    @staticmethod
    def load_from_json(file_path: str) -> PromptTemplate:
        """
        从JSON文件加载提示词模板
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            提示词模板对象
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return PromptTemplate(
            name=data['name'],
            system_prompt=data['system_prompt'],
            user_prompt=data.get('user_prompt', '')
        )
    
    @staticmethod
    def create_simple_template(name: str, system_prompt: str, user_prompt: str = "") -> PromptTemplate:
        """
        创建简单的提示词模板
        
        Args:
            name: 模板名称
            system_prompt: 系统提示词
            user_prompt: 用户提示词（可选）
            
        Returns:
            提示词模板对象
        """
        return PromptTemplate(
            name=name,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )