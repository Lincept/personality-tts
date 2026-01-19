"""
OpenAI 兼容的 LLM 流式调用封装
支持所有兼容 OpenAI API 的大模型服务
支持 Function Calling（工具调用）
"""
from openai import OpenAI
from typing import Generator, Optional, Dict, Any, List, Callable
import json


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

    def chat_stream_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_executor: Optional[Callable[[str, Dict], str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_tool_calls: int = 5
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式聊天（支持工具调用）

        当 LLM 调用工具时，会自动执行工具并继续对话

        Args:
            messages: 消息列表
            tools: 工具定义列表（OpenAI function calling 格式）
            tool_executor: 工具执行器函数 (tool_name, arguments) -> result
            temperature: 温度参数
            max_tokens: 最大 token 数
            max_tool_calls: 最大工具调用次数（防止无限循环）

        Yields:
            事件字典:
            - {"type": "content", "data": "文本片段"}  # 文本内容
            - {"type": "tool_call", "data": {"name": "工具名", "arguments": {...}}}  # 工具调用
            - {"type": "tool_result", "data": "工具结果"}  # 工具执行结果
            - {"type": "error", "data": "错误信息"}  # 错误
        """
        if not tools or not tool_executor:
            # 没有工具，使用普通流式对话
            for chunk in self.chat_stream(messages, temperature, max_tokens):
                yield {"type": "content", "data": chunk}
            return

        current_messages = messages.copy()
        tool_call_count = 0

        while tool_call_count < max_tool_calls:
            try:
                # 发起请求
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=current_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice="auto",
                    stream=True
                )

                # 收集响应
                accumulated_content = ""
                tool_calls = []
                current_tool_call = None

                for chunk in response:
                    delta = chunk.choices[0].delta

                    # 处理文本内容
                    if delta.content:
                        accumulated_content += delta.content
                        yield {"type": "content", "data": delta.content}

                    # 处理工具调用
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            idx = tool_call_delta.index

                            # 初始化或更新工具调用
                            while len(tool_calls) <= idx:
                                tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })

                            if tool_call_delta.id:
                                tool_calls[idx]["id"] = tool_call_delta.id

                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    tool_calls[idx]["function"]["name"] = tool_call_delta.function.name

                                if tool_call_delta.function.arguments:
                                    tool_calls[idx]["function"]["arguments"] += tool_call_delta.function.arguments

                # 检查是否有工具调用
                if not tool_calls:
                    # 没有工具调用，对话结束
                    break

                # 执行工具调用
                tool_call_count += 1

                # 将助手的响应添加到消息历史
                assistant_message = {"role": "assistant", "content": accumulated_content or None}

                # 如果有工具调用，添加到消息中
                if tool_calls:
                    assistant_message["tool_calls"] = tool_calls

                current_messages.append(assistant_message)

                # 执行每个工具调用
                for tool_call in tool_calls:
                    function_name = tool_call["function"]["name"]
                    try:
                        function_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        function_args = {}

                    yield {
                        "type": "tool_call",
                        "data": {
                            "name": function_name,
                            "arguments": function_args
                        }
                    }

                    # 执行工具
                    try:
                        tool_result = tool_executor(function_name, function_args)
                        yield {"type": "tool_result", "data": tool_result}

                        # 添加工具结果到消息历史
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": tool_result
                        })

                    except Exception as e:
                        error_msg = f"工具执行错误: {str(e)}"
                        yield {"type": "error", "data": error_msg}

                        # 将错误也添加到消息历史
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": error_msg
                        })

                # 继续循环，让 LLM 根据工具结果生成下一轮响应

            except Exception as e:
                yield {"type": "error", "data": f"请求错误: {str(e)}"}
                break

        if tool_call_count >= max_tool_calls:
            yield {"type": "error", "data": "达到最大工具调用次数限制"}

    def chat_json_object(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        JSON Object 模式调用（非流式）

        使用 response_format={"type": "json_object"} 确保输出为标准 JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            解析后的 JSON 字典

        Raises:
            json.JSONDecodeError: JSON 解析失败
            Exception: API 调用失败
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        content = response.choices[0].message.content
        return json.loads(content)

    def chat_json_object_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Generator[str, None, str]:
        """
        JSON Object 模式流式调用

        注意：流式输出需要收集完整内容后才能解析 JSON
        此方法先收集完整响应，然后解析并返回指定字段

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        Yields:
            原始文本片段（用于进度显示）

        Returns:
            完整的 JSON 字符串
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

        full_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_content += text
                yield text

        return full_content
