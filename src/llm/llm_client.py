"""
OpenAI 兼容的 LLM 流式调用封装
支持所有兼容 OpenAI API 的大模型服务
"""
from openai import OpenAI
from typing import Generator, Optional, Dict, Any


class LLMClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4"):
        """
        初始化 LLM 客户端

        Args:
            api_key: API Key
            base_url: API 基础URL (支持OpenAI兼容接口)
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages: list, temperature: float = 0.7,
             max_tokens: int = 2000, stream: bool = False) -> Any:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出

        Returns:
            响应内容或生成器
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )

            if stream:
                return self._stream_response(response)
            else:
                return {
                    "success": True,
                    "content": response.choices[0].message.content,
                    "model": self.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self.model
            }

    def _stream_response(self, response) -> Generator[str, None, None]:
        """
        处理流式响应

        Args:
            response: OpenAI 响应对象

        Yields:
            文本片段
        """
        try:
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[Error: {str(e)}]"

    def chat_stream(self, messages: list, temperature: float = 0.7,
                    max_tokens: int = 2000) -> Generator[str, None, None]:
        """
        流式聊天（便捷方法）

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数

        Yields:
            文本片段
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\n[Error: {str(e)}]"

    def simple_chat(self, prompt: str, system_prompt: Optional[str] = None,
                    temperature: float = 0.7, stream: bool = False) -> Any:
        """
        简单对话接口

        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            temperature: 温度参数
            stream: 是否流式输出

        Returns:
            响应内容或生成器
        """
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        return self.chat(messages, temperature=temperature, stream=stream)

    def get_model_info(self) -> Dict[str, str]:
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "model": self.model,
            "base_url": self.base_url,
            "provider": self._detect_provider()
        }

    def _detect_provider(self) -> str:
        """
        检测服务提供商

        Returns:
            提供商名称
        """
        if "openai.com" in self.base_url:
            return "OpenAI"
        elif "anthropic.com" in self.base_url:
            return "Anthropic"
        elif "dashscope.aliyuncs.com" in self.base_url:
            return "Qwen"
        elif "api.minimax.chat" in self.base_url:
            return "MiniMax"
        elif "generativelanguage.googleapis.com" in self.base_url:
            return "Google"
        else:
            return "Custom"
