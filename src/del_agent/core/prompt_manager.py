"""
Prompt Manager - 提示词管理模块
支持从YAML/JSON文件加载结构化提示词模板
"""

import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from jinja2 import Template, Environment, BaseLoader

logger = logging.getLogger(__name__)


class PromptTemplate:
    """
    提示词模板类
    封装单个提示词模板，支持变量替换
    """
    
    def __init__(self, name: str, system_prompt: str, user_prompt: str = ""):
        """
        初始化提示词模板
        
        Args:
            name: 模板名称
            system_prompt: 系统提示词
            user_prompt: 用户提示词（可选）
        """
        self.name = name
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.jinja_env = Environment(loader=BaseLoader())
        
        # 预编译模板以提高性能
        self._system_template = self.jinja_env.from_string(system_prompt)
        if user_prompt:
            self._user_template = self.jinja_env.from_string(user_prompt)
        else:
            self._user_template = None
    
    def render(self, **kwargs) -> Dict[str, str]:
        """
        渲染模板
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            包含渲染后提示词的字典
        """
        try:
            rendered_system = self._system_template.render(**kwargs)
            rendered_user = self._user_template.render(**kwargs) if self._user_template else ""
            
            return {
                "system": rendered_system,
                "user": rendered_user
            }
        except Exception as e:
            logger.error(f"Error rendering template '{self.name}': {str(e)}")
            raise ValueError(f"Failed to render template '{self.name}': {str(e)}")
    
    def render_messages(self, **kwargs) -> list:
        """
        渲染为消息格式
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            OpenAI格式的消息列表
        """
        rendered = self.render(**kwargs)
        messages = []
        
        if rendered["system"]:
            messages.append({"role": "system", "content": rendered["system"]})
        
        if rendered["user"]:
            messages.append({"role": "user", "content": rendered["user"]})
        
        return messages


class PromptManager:
    """
    提示词管理器
    负责加载、管理和提供提示词模板
    """
    
    def __init__(self, templates_dir: Optional[Union[str, Path]] = None):
        """
        初始化提示词管理器
        
        Args:
            templates_dir: 模板目录路径
        """
        self.templates: Dict[str, PromptTemplate] = {}
        self.templates_dir = Path(templates_dir) if templates_dir else None
        self.logger = logging.getLogger(__name__)
        
        # 如果指定了模板目录，自动加载
        if self.templates_dir and self.templates_dir.exists():
            self.load_templates_from_directory(self.templates_dir)
    
    def load_template_from_file(self, file_path: Union[str, Path]) -> PromptTemplate:
        """
        从文件加载模板
        
        Args:
            file_path: 模板文件路径
            
        Returns:
            提示词模板对象
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")
        
        try:
            # 根据文件扩展名选择加载方式
            if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                raise ValueError(f"Unsupported template file format: {file_path.suffix}")
            
            # 验证必需字段
            if 'name' not in data or 'system_prompt' not in data:
                raise ValueError("Template must contain 'name' and 'system_prompt' fields")
            
            # 创建模板对象
            template = PromptTemplate(
                name=data['name'],
                system_prompt=data['system_prompt'],
                user_prompt=data.get('user_prompt', '')
            )
            
            self.logger.info(f"Loaded template '{template.name}' from {file_path}")
            return template
            
        except Exception as e:
            self.logger.error(f"Error loading template from {file_path}: {str(e)}")
            raise ValueError(f"Failed to load template from {file_path}: {str(e)}")
    
    def load_templates_from_directory(self, directory: Union[str, Path]) -> None:
        """
        从目录批量加载模板
        
        Args:
            directory: 模板目录路径
        """
        directory = Path(directory)
        
        if not directory.exists():
            self.logger.warning(f"Templates directory not found: {directory}")
            return
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        # 支持的文件扩展名
        supported_extensions = {'.yaml', '.yml', '.json'}
        
        loaded_count = 0
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    template = self.load_template_from_file(file_path)
                    self.register_template(template)
                    loaded_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to load template from {file_path}: {str(e)}")
        
        self.logger.info(f"Loaded {loaded_count} templates from {directory}")
    
    def register_template(self, template: PromptTemplate) -> None:
        """
        注册模板
        
        Args:
            template: 提示词模板对象
        """
        if template.name in self.templates:
            self.logger.warning(f"Overwriting existing template: {template.name}")
        
        self.templates[template.name] = template
        self.logger.debug(f"Registered template: {template.name}")
    
    def get_template(self, name: str) -> PromptTemplate:
        """
        获取模板
        
        Args:
            name: 模板名称
            
        Returns:
            提示词模板对象
            
        Raises:
            KeyError: 如果模板不存在
        """
        if name not in self.templates:
            raise KeyError(f"Template not found: {name}")
        
        return self.templates[name]
    
    def render_template(self, name: str, **kwargs) -> Dict[str, str]:
        """
        渲染模板
        
        Args:
            name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            包含渲染后提示词的字典
        """
        template = self.get_template(name)
        return template.render(**kwargs)
    
    def render_messages(self, name: str, **kwargs) -> list:
        """
        渲染为消息格式
        
        Args:
            name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            OpenAI格式的消息列表
        """
        template = self.get_template(name)
        return template.render_messages(**kwargs)
    
    def list_templates(self) -> list:
        """
        列出所有可用的模板
        
        Returns:
            模板名称列表
        """
        return list(self.templates.keys())
    
    def has_template(self, name: str) -> bool:
        """
        检查模板是否存在
        
        Args:
            name: 模板名称
            
        Returns:
            是否存在该模板
        """
        return name in self.templates


# 全局提示词管理器实例
_default_manager = None


def get_default_prompt_manager() -> PromptManager:
    """
    获取默认的提示词管理器
    
    Returns:
        默认的PromptManager实例
    """
    global _default_manager
    
    if _default_manager is None:
        # 尝试从默认位置加载模板
        default_templates_dir = Path(__file__).parent.parent / "prompts" / "templates"
        _default_manager = PromptManager(default_templates_dir)
    
    return _default_manager