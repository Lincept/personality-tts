"""
LLM Adapter Layer - 模型适配层
提供统一的LLM接口，支持多种模型服务商
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
import json
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    LLM提供者抽象基类
    定义统一的LLM接口，支持不同的模型服务商
    """
    
    def __init__(self, model_name: str, **kwargs):
        """
        初始化LLM提供者
        
        Args:
            model_name: 模型名称
            **kwargs: 其他配置参数
        """
        self.model_name = model_name
        self.config = kwargs
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        生成文本
        
        Args:
            messages: 消息列表，格式为 [{"role": "system/user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
        """
        pass
    
    @abstractmethod
    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_format: Type[BaseModel],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> BaseModel:
        """
        生成结构化输出
        
        Args:
            messages: 消息列表
            response_format: Pydantic模型类
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            Pydantic模型实例
        """
        pass


class OpenAICompatibleProvider(LLMProvider):
    """
    OpenAI兼容的LLM提供者
    支持DeepSeek、Moonshot等兼容OpenAI API格式的服务商
    """
    
    def __init__(
        self, 
        model_name: str,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: int = 30,
        api_secret: Optional[str] = None,
        reasoning_effort: str = "minimal",
        **kwargs
    ):
        """
        初始化OpenAI兼容提供者
        
        Args:
            model_name: 模型名称
            api_key: API密钥
            base_url: 基础URL，默认为OpenAI官方地址
            timeout: 超时时间
            api_secret: API密钥（用于豆包等需要双密钥的服务商）
            reasoning_effort: 推理强度（豆包专用）：minimal/low/medium/high，默认minimal（不思考）
            **kwargs: 其他配置参数
        """
        super().__init__(model_name, **kwargs)

        self.base_url = base_url
        self._is_ark_endpoint = bool(base_url and "volces.com" in base_url)
        self.reasoning_effort = reasoning_effort
        
        # 禁用代理 - 通过环境变量
        os.environ['NO_PROXY'] = '*'
        os.environ['no_proxy'] = '*'
        
        # 创建OpenAI客户端
        client_kwargs = {
            "api_key": api_key
        }
        if base_url:
            client_kwargs["base_url"] = base_url
        if timeout:
            client_kwargs["timeout"] = timeout
        
        # 豆包特殊处理
        if api_secret:
            self.logger.info(f"Configured with API secret for enhanced authentication")
        
        self.client = OpenAI(**client_kwargs)
        self.logger.info(f"Initialized OpenAI-compatible provider with model: {model_name}")

    def _fix_nested_type_names(self, data: Dict[str, Any], schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        修复 LLM 返回的嵌套类型名称问题
        例如: {"extracted_review": {"RawReview": {...}}} → {"extracted_review": {...}}
        
        Args:
            data: 原始 JSON 数据
            schema: Pydantic 模型类
            
        Returns:
            修复后的 JSON 数据
        """
        if not isinstance(data, dict):
            return data
        
        fixed_data = {}
        annotations = getattr(schema, '__annotations__', {})
        
        for key, value in data.items():
            if isinstance(value, dict) and len(value) == 1:
                # 检查是否是嵌套类型名的情况
                nested_key = list(value.keys())[0]
                nested_value = value[nested_key]
                
                # 如果嵌套键看起来像类型名（首字母大写）且内部值是字典
                if nested_key and nested_key[0].isupper() and isinstance(nested_value, dict):
                    # 直接使用内部值
                    self.logger.debug(f"Auto-fixing nested type name: {key}.{nested_key} -> {key}")
                    fixed_data[key] = nested_value
                else:
                    fixed_data[key] = value
            else:
                fixed_data[key] = value
        
        return fixed_data

    def _apply_ark_thinking_override(self, request_params: Dict[str, Any]) -> None:
        """对方舟(ARK)端点设置 reasoning_effort 参数。"""
        if self._is_ark_endpoint:
            # 豆包 API 使用 reasoning_effort 控制推理程度
            # minimal: 不思考, low/medium/high: 不同程度的思考
            request_params.pop("thinking", None)  # 移除可能存在的thinking参数
            request_params["reasoning_effort"] = self.reasoning_effort
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        生成文本
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
        """
        try:
            self.logger.debug(f"Generating text with {len(messages)} messages")
            
            # 构建请求参数
            request_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
                
            # 添加其他参数
            request_params.update(kwargs)

            # 方舟端点：强制关闭 thinking
            self._apply_ark_thinking_override(request_params)
            
            # 调用API
            response = self.client.chat.completions.create(**request_params)
            
            # 提取生成的内容
            content = response.choices[0].message.content
            self.logger.debug(f"Generated content length: {len(content) if content else 0}")
            
            return content or ""
            
        except Exception as e:
            self.logger.error(f"Error generating text: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_format: Type[BaseModel],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> BaseModel:
        """
        生成结构化输出
        
        Args:
            messages: 消息列表
            response_format: Pydantic模型类
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            Pydantic模型实例
        """
        try:
            self.logger.debug(f"Generating structured output for {response_format.__name__}")
            
            # 获取 Pydantic schema
            schema_dict = response_format.model_json_schema()
            schema_properties = schema_dict.get('properties', {})
            
            # 构建字段说明
            required_fields = schema_dict.get('required', [])
            field_descriptions = []
            for field_name, field_info in schema_properties.items():
                field_type = field_info.get('type', 'any')
                field_desc = field_info.get('description', '')
                is_required = field_name in required_fields
                required_mark = " (required)" if is_required else " (optional)"
                field_descriptions.append(f"  - {field_name}: {field_type}{required_mark} - {field_desc}")
            
            fields_text = "\n".join(field_descriptions) if field_descriptions else "  (no specific fields)"
            
            # 添加JSON格式指示到系统消息
            json_instruction = (
                f"You must respond with valid JSON that matches the expected schema.\n"
                f"Expected JSON fields:\n{fields_text}\n\n"
                "Do not include any explanations or markdown formatting. "
                "Return only the JSON object with the specified field names."
            )
            
            # 修改消息，确保第一个消息是系统消息
            modified_messages = messages.copy()
            if modified_messages and modified_messages[0]["role"] == "system":
                modified_messages[0]["content"] = f"{modified_messages[0]['content']}\n\n{json_instruction}"
            else:
                modified_messages.insert(0, {"role": "system", "content": json_instruction})
            
            # 构建请求参数
            request_params = {
                "model": self.model_name,
                "messages": modified_messages,
                "temperature": temperature,
                "response_format": {"type": "json_object"}
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
                
            # 添加其他参数
            request_params.update(kwargs)

            # 方舟端点：强制关闭 thinking
            self._apply_ark_thinking_override(request_params)
            
            # 调用API
            response = self.client.chat.completions.create(**request_params)
            
            # 提取生成的内容
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")
            
            self.logger.debug(f"Raw JSON response: {content}")
            
            # 解析JSON
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON response: {content}")
                raise ValueError(f"LLM returned invalid JSON: {str(e)}")
            
            # 自动修复嵌套的类型名称问题
            # 例如 {"extracted_review": {"RawReview": {...}}} → {"extracted_review": {...}}
            json_data = self._fix_nested_type_names(json_data, response_format)
            
            # 验证并创建Pydantic模型实例
            try:
                result = response_format(**json_data)
                self.logger.debug(f"Successfully validated structured output: {result}")
                return result
            except Exception as e:
                self.logger.error(f"Failed to validate response against schema: {str(e)}")
                self.logger.error(f"JSON data: {json_data}")
                self.logger.error(f"Expected schema: {response_format.__annotations__}")
                raise ValueError(f"Response validation failed: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Error generating structured output: {str(e)}")
            raise