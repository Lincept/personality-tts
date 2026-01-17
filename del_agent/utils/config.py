"""
Configuration utilities for AI Data Factory
配置管理工具
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel
from dotenv import load_dotenv

from ..models.schemas import LLMConfig, AgentConfig


class ConfigManager:
    """
    配置管理器
    统一管理项目的所有配置
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载环境变量（优先从 del_agent 目录下查找 .env）
        env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path=env_path if env_path.exists() else None)
        
        if config_path:
            self.config_path = Path(config_path)
        else:
            default_config = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
            self.config_path = default_config if default_config.exists() else None
        self.llm_configs: Dict[str, LLMConfig] = {}
        self.agent_configs: Dict[str, AgentConfig] = {}
        self.global_config: Dict[str, Any] = {}
        
        # 如果指定了配置文件，自动加载
        if self.config_path and self.config_path.exists():
            self.load_config(self.config_path)
        else:
            # 加载默认配置
            self._load_default_config()
    
    def load_config(self, config_path: Union[str, Path]) -> None:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            # 解析配置
            self._parse_config(config_data)
            
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {str(e)}")
    
    def _parse_config(self, config_data: Dict[str, Any]) -> None:
        """
        解析配置数据
        
        Args:
            config_data: 配置数据字典
        """
        # 全局配置
        self.global_config = config_data.get('global', {})
        
        # LLM配置
        llm_configs_data = config_data.get('llm_providers', {})
        for name, config in llm_configs_data.items():
            # 从环境变量获取API密钥（如果配置文件中未设置或为空）
            if 'api_key' not in config or not config['api_key']:
                # 根据提供者名称映射到对应的环境变量
                env_key_map = {
                    'doubao': 'DOBAO_API_KEY',
                    'openai': 'OPENAI_API_KEY',
                    'deepseek': 'DEEPSEEK_API_KEY',
                    'moonshot': 'MOONSHOT_API_KEY',
                    'qwen': 'QWEN_API_KEY',
                }
                env_key = env_key_map.get(name, f"{name.upper()}_API_KEY")
                config['api_key'] = os.getenv(env_key, os.getenv('LLM_API_KEY', ''))
            
            # 从环境变量获取API密钥（用于豆包等需要双密钥的服务商）
            if name == 'doubao' and ('api_secret' not in config or not config['api_secret']):
                config['api_secret'] = os.getenv('DOBAO_API_SECRET', '')
            
            self.llm_configs[name] = LLMConfig(**config)
        
        # Agent配置
        agent_configs_data = config_data.get('agents', {})
        for name, config in agent_configs_data.items():
            # 解析LLM配置引用
            llm_provider_name = config.get('llm_provider')
            if llm_provider_name and llm_provider_name in self.llm_configs:
                config['llm_config'] = self.llm_configs[llm_provider_name]
            elif 'llm_config' in config:
                config['llm_config'] = LLMConfig(**config['llm_config'])
            else:
                raise ValueError(f"LLM provider not found for agent '{name}': {llm_provider_name}")
            
            self.agent_configs[name] = AgentConfig(**config)
    
    def _load_default_config(self) -> None:
        """
        加载默认配置
        """
        # 默认LLM配置 - 将豆包设为默认
        default_api_key = os.getenv('LLM_API_KEY', '')
        
        # 豆包配置（默认）
        self.llm_configs['doubao'] = LLMConfig(
            provider='doubao',
            model_name='ERNIE-Bot-4',
            api_key=os.getenv('DOBAO_API_KEY', default_api_key),
            api_secret=os.getenv('DOBAO_API_SECRET'),
            base_url='https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro',
            temperature=0.7
        )
        
        # OpenAI配置
        self.llm_configs['openai'] = LLMConfig(
            provider='openai',
            model_name='gpt-3.5-turbo',
            api_key=os.getenv('OPENAI_API_KEY', default_api_key),
            base_url=None,
            temperature=0.7
        )
        
        # DeepSeek配置
        self.llm_configs['deepseek'] = LLMConfig(
            provider='deepseek',
            model_name='deepseek-chat',
            api_key=os.getenv('DEEPSEEK_API_KEY', default_api_key),
            base_url='https://api.deepseek.com',
            temperature=0.7
        )
        
        # 通义千问配置
        self.llm_configs['qwen'] = LLMConfig(
            provider='qwen',
            model_name='qwen-plus',
            api_key=os.getenv('QWEN_API_KEY', default_api_key),
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            temperature=0.7
        )
        
        # 默认Agent配置 - 使用豆包作为默认LLM
        self.agent_configs['comment_cleaner'] = AgentConfig(
            name='comment_cleaner',
            description='原始评论清洗智能体',
            llm_config=self.llm_configs['doubao'],
            prompt_template='comment_cleaner',
            max_retries=3
        )
    
    def get_llm_config(self, name: str) -> LLMConfig:
        """
        获取LLM配置
        
        Args:
            name: 配置名称
            
        Returns:
            LLM配置对象
        """
        if name not in self.llm_configs:
            raise KeyError(f"LLM config not found: {name}")
        
        return self.llm_configs[name]
    
    def get_agent_config(self, name: str) -> AgentConfig:
        """
        获取Agent配置
        
        Args:
            name: 配置名称
            
        Returns:
            Agent配置对象
        """
        if name not in self.agent_configs:
            raise KeyError(f"Agent config not found: {name}")
        
        return self.agent_configs[name]
    
    def get_global_config(self, key: str, default: Any = None) -> Any:
        """
        获取全局配置
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.global_config.get(key, default)
    
    def list_llm_configs(self) -> list:
        """
        列出所有LLM配置
        
        Returns:
            配置名称列表
        """
        return list(self.llm_configs.keys())
    
    def list_agent_configs(self) -> list:
        """
        列出所有Agent配置
        
        Returns:
            配置名称列表
        """
        return list(self.agent_configs.keys())
    
    def save_config(self, config_path: Union[str, Path]) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径
        """
        config_path = Path(config_path)
        
        config_data = {
            'global': self.global_config,
            'llm_providers': {
                name: config.dict() for name, config in self.llm_configs.items()
            },
            'agents': {
                name: config.dict() for name, config in self.agent_configs.items()
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.safe_dump(config_data, f, indent=2, allow_unicode=True)
                elif config_path.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
        except Exception as e:
            raise ValueError(f"Failed to save config to {config_path}: {str(e)}")


# 全局配置管理器实例
_default_config_manager = None


def get_config_manager(config_path: Optional[Union[str, Path]] = None) -> ConfigManager:
    """
    获取默认的配置管理器
    
    Args:
        config_path: 配置文件路径（可选）
        
    Returns:
        配置管理器实例
    """
    global _default_config_manager
    
    if _default_config_manager is None:
        _default_config_manager = ConfigManager(config_path)
    
    return _default_config_manager