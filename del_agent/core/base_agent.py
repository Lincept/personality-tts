"""
Base Agent Structure - 智能体基类
定义统一的智能体接口和生命周期
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, List, TYPE_CHECKING
import logging
import time
from datetime import datetime
from pydantic import BaseModel

from .llm_adapter import LLMProvider
from .prompt_manager import PromptManager, get_default_prompt_manager

# 避免循环导入
if TYPE_CHECKING:
    from .verification import VerificationLoop
    from ..models.schemas import CriticFeedback


class AgentResult(BaseModel):
    """
    智能体执行结果基类
    所有智能体的输出都应该继承此类
    """
    success: bool = True
    error_message: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = ""
    metadata: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if not data.get('timestamp'):
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)


class BaseAgent(ABC):
    """
    智能体基类
    定义统一的智能体接口和生命周期管理
    """
    
    def __init__(
        self,
        name: str,
        llm_provider: LLMProvider,
        prompt_manager: Optional[PromptManager] = None,
        **kwargs
    ):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            llm_provider: LLM提供者
            prompt_manager: 提示词管理器（可选）
            **kwargs: 其他配置参数
        """
        self.name = name
        self.llm_provider = llm_provider
        self.prompt_manager = prompt_manager or get_default_prompt_manager()
        self.config = kwargs
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}.{name}")
        
        # 初始化统计信息
        self.execution_count = 0
        self.total_execution_time = 0.0
        
        self.logger.info(f"Initialized agent: {name}")
    
    @abstractmethod
    def get_output_schema(self) -> Type[BaseModel]:
        """
        获取输出模式
        子类必须实现此方法，返回对应的Pydantic模型类
        
        Returns:
            Pydantic模型类
        """
        pass
    
    @abstractmethod
    def get_prompt_template_name(self) -> str:
        """
        获取提示词模板名称
        子类必须实现此方法，返回使用的提示词模板名称
        
        Returns:
            提示词模板名称
        """
        pass
    
    def prepare_input(self, raw_input: Any, **kwargs) -> Dict[str, Any]:
        """
        准备输入数据
        子类可以重写此方法以自定义输入处理逻辑
        
        Args:
            raw_input: 原始输入数据
            **kwargs: 其他参数
            
        Returns:
            处理后的输入数据字典
        """
        return {
            "input": raw_input,
            **kwargs
        }
    
    def validate_output(self, output: BaseModel) -> bool:
        """
        验证输出数据
        子类可以重写此方法以添加自定义验证逻辑
        
        Args:
            output: 输出数据
            
        Returns:
            是否验证通过
        """
        return True
    
    def process(self, raw_input: Any, **kwargs) -> BaseModel:
        """
        处理输入数据的主方法
        
        Args:
            raw_input: 原始输入数据
            **kwargs: 其他参数
            
        Returns:
            处理结果（Pydantic模型实例）
        """
        start_time = time.time()
        self.execution_count += 1
        
        try:
            self.logger.info(f"Processing input: {type(raw_input).__name__}")
            
            # 准备输入数据
            input_data = self.prepare_input(raw_input, **kwargs)
            self.logger.debug(f"Prepared input data: {input_data}")
            
            # 获取提示词模板
            template_name = self.get_prompt_template_name()
            if not self.prompt_manager.has_template(template_name):
                raise ValueError(f"Prompt template not found: {template_name}")
            
            # 渲染提示词
            messages = self.prompt_manager.render_messages(template_name, **input_data)
            self.logger.debug(f"Rendered messages: {len(messages)} messages")
            
            # 获取输出模式
            output_schema = self.get_output_schema()
            
            # 调用LLM生成结构化输出
            self.logger.info("Calling LLM for structured output")
            llm_result = self.llm_provider.generate_structured(
                messages=messages,
                response_format=output_schema,
                **self.config.get('llm_params', {})
            )
            
            # 验证输出
            if not self.validate_output(llm_result):
                raise ValueError("Output validation failed")
            
            # 计算执行时间
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            # 更新结果元数据
            if hasattr(llm_result, 'metadata'):
                llm_result.metadata.update({
                    'agent_name': self.name,
                    'execution_time': execution_time,
                    'input_type': type(raw_input).__name__,
                    'template_used': template_name
                })
            
            self.logger.info(f"Processing completed in {execution_time:.2f}s")
            return llm_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Processing failed after {execution_time:.2f}s: {str(e)}")
            
            # 创建错误结果
            error_result = self.get_output_schema()(
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
            
            return error_result
    
    def process_with_verification(
        self,
        raw_input: Any,
        critic_agent: Optional['BaseAgent'] = None,
        max_retries: int = 3,
        strictness_level: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """
        带核验循环的处理流程
        
        这是 Phase 1 新增的核心方法，实现 Verification Loop：
        Input → Process → Critic Check → Pass/Retry
        
        Args:
            raw_input: 原始输入数据
            critic_agent: 判别器智能体（可选）
                - 如果为 None，回退到标准 process() 流程
                - 必须实现 evaluate(output, context) 方法
            max_retries: 最大重试次数
            strictness_level: 严格度等级（0.0-1.0）
            **kwargs: 传递给 process() 的其他参数
        
        Returns:
            处理结果（Pydantic 模型实例）
            结果的 metadata 字段会附加 feedback_history
        
        Example:
            # 创建智能体和判别器
            cleaner = RawCommentCleaner(llm_provider)
            critic = CriticAgent(llm_provider)
            
            # 使用核验循环
            result = cleaner.process_with_verification(
                raw_input="这老板简直是'学术妲己'！",
                critic_agent=critic,
                max_retries=3
            )
            
            # 查看反馈历史
            print(result.metadata['feedback_history'])
        """
        # 如果没有提供判别器，回退到标准流程
        if critic_agent is None:
            self.logger.info("No critic agent provided, using standard process()")
            return self.process(raw_input, **kwargs)
        
        # 延迟导入以避免循环依赖
        from .verification import VerificationLoop
        from ..models.schemas import CriticFeedback
        
        self.logger.info(
            f"Starting process with verification: "
            f"max_retries={max_retries}, strictness={strictness_level}"
        )
        
        # 创建核验循环器
        verification_loop = VerificationLoop(
            max_retries=max_retries,
            strictness_level=strictness_level,
            enable_logging=True
        )
        
        # 定义生成器函数（无参数）
        def generator() -> BaseModel:
            return self.process(raw_input, **kwargs)
        
        # 定义判别器函数
        def critic(output: BaseModel, context: Any) -> CriticFeedback:
            # 检查 critic_agent 是否有 evaluate 方法
            if hasattr(critic_agent, 'evaluate'):
                return critic_agent.evaluate(output, context)
            else:
                # 如果没有 evaluate 方法，使用 process 方法
                # 需要将 output 和 context 打包传递
                evaluation_input = {
                    "agent_output": output.dict() if hasattr(output, 'dict') else str(output),
                    "original_input": str(context),
                    "strictness_level": strictness_level
                }
                feedback_result = critic_agent.process(evaluation_input)
                
                # 确保返回的是 CriticFeedback
                if isinstance(feedback_result, CriticFeedback):
                    return feedback_result
                else:
                    # 如果不是，尝试转换
                    return CriticFeedback(
                        is_approved=getattr(feedback_result, 'is_approved', True),
                        reasoning=getattr(feedback_result, 'reasoning', ''),
                        suggestion=getattr(feedback_result, 'suggestion', ''),
                        confidence_score=getattr(feedback_result, 'confidence_score', 1.0)
                    )
        
        # 执行核验循环
        result, feedback_history = verification_loop.execute(
            generator_func=generator,
            critic_func=critic,
            context=raw_input
        )
        
        # 将反馈历史附加到结果的元数据中
        if hasattr(result, 'metadata'):
            if not isinstance(result.metadata, dict):
                result.metadata = {}
            result.metadata['feedback_history'] = [
                fb.dict() if hasattr(fb, 'dict') else fb
                for fb in feedback_history
            ]
            result.metadata['verification_stats'] = {
                'total_attempts': len(feedback_history),
                'final_approval': feedback_history[-1].is_approved if feedback_history else False,
                'max_retries': max_retries,
                'strictness_level': strictness_level
            }
        
        self.logger.info(
            f"Verification completed: "
            f"attempts={len(feedback_history)}, "
            f"approved={feedback_history[-1].is_approved if feedback_history else False}"
        )
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取智能体统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.total_execution_time / max(self.execution_count, 1),
            "llm_provider": self.llm_provider.__class__.__name__,
            "model_name": self.llm_provider.model_name
        }
    
    def reset_stats(self) -> None:
        """
        重置统计信息
        """
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.logger.info("Agent statistics reset")


class SimpleAgent(BaseAgent):
    """
    简单智能体实现
    用于快速原型开发和测试
    """
    
    def __init__(
        self,
        name: str,
        llm_provider: LLMProvider,
        output_schema: Type[BaseModel],
        prompt_template_name: str,
        prompt_manager: Optional[PromptManager] = None,
        **kwargs
    ):
        """
        初始化简单智能体
        
        Args:
            name: 智能体名称
            llm_provider: LLM提供者
            output_schema: 输出模式
            prompt_template_name: 提示词模板名称
            prompt_manager: 提示词管理器（可选）
            **kwargs: 其他配置参数
        """
        super().__init__(name, llm_provider, prompt_manager, **kwargs)
        self._output_schema = output_schema
        self._prompt_template_name = prompt_template_name
    
    def get_output_schema(self) -> Type[BaseModel]:
        """获取输出模式"""
        return self._output_schema
    
    def get_prompt_template_name(self) -> str:
        """获取提示词模板名称"""
        return self._prompt_template_name