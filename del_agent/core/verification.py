"""
Verification Loop - 核验循环机制
实现 Agent Output → Critic Check → Pass/Retry 的核心逻辑
"""

from typing import Callable, Tuple, List, Any, Optional
from pydantic import BaseModel
import logging
import time
from datetime import datetime

# 延迟导入以避免循环依赖
try:
    from ..models.schemas import CriticFeedback
except (ImportError, ValueError):
    # 如果相对导入失败，尝试绝对导入
    from models.schemas import CriticFeedback

logger = logging.getLogger(__name__)


class VerificationLoop:
    """
    核验循环器
    
    核心功能：
    1. 执行生成器函数，产生 Agent 输出
    2. 调用判别器函数，评估输出质量
    3. 根据判别结果决定是否重试
    4. 记录完整的反馈历史
    
    设计模式：Strategy Pattern（策略模式）
    
    使用示例：
        loop = VerificationLoop(max_retries=3, strictness_level=0.7)
        result, history = loop.execute(
            generator_func=lambda: agent.process(input_data),
            critic_func=lambda output, ctx: critic.evaluate(output, ctx),
            context=original_input
        )
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        strictness_level: float = 0.7,
        enable_logging: bool = True
    ):
        """
        初始化核验循环器
        
        Args:
            max_retries: 最大重试次数（不包括首次尝试）
            strictness_level: 严格度等级，0.0-1.0
                - 0.5: 宽松（允许轻微偏差）
                - 0.7: 标准（正常质量要求）
                - 0.9: 严格（要求近乎完美）
            enable_logging: 是否启用详细日志
        """
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if not 0 <= strictness_level <= 1:
            raise ValueError("strictness_level must be between 0 and 1")
        
        self.max_retries = max_retries
        self.strictness_level = strictness_level
        self.enable_logging = enable_logging
        
        # 统计信息
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        
        if enable_logging:
            logger.info(
                f"VerificationLoop initialized: "
                f"max_retries={max_retries}, strictness={strictness_level}"
            )
    
    def execute(
        self,
        generator_func: Callable[[], BaseModel],
        critic_func: Callable[[BaseModel, Any], CriticFeedback],
        context: Any = None
    ) -> Tuple[BaseModel, List[CriticFeedback]]:
        """
        执行核验循环
        
        Args:
            generator_func: 生成器函数，无参数，返回 Pydantic 模型实例
                示例: lambda: agent.process(input_data)
            critic_func: 判别器函数，接收 (output, context)，返回 CriticFeedback
                示例: lambda output, ctx: critic.evaluate(output, ctx)
            context: 上下文信息（通常是原始输入），传递给判别器
        
        Returns:
            Tuple[BaseModel, List[CriticFeedback]]:
                - 最终输出结果（Pydantic 模型实例）
                - 所有反馈历史列表
        
        Raises:
            Exception: 如果生成器或判别器抛出异常
        """
        self.total_executions += 1
        feedback_history: List[CriticFeedback] = []
        output: Optional[BaseModel] = None
        
        start_time = time.time()
        total_attempts = self.max_retries + 1  # 包括首次尝试
        
        if self.enable_logging:
            logger.info(f"Starting verification loop (max attempts: {total_attempts})")
        
        for attempt in range(total_attempts):
            try:
                # Step 1: 生成输出
                if self.enable_logging:
                    logger.debug(f"Attempt {attempt + 1}/{total_attempts}: Generating output...")
                
                generation_start = time.time()
                output = generator_func()
                generation_time = time.time() - generation_start
                
                if self.enable_logging:
                    logger.debug(f"Output generated in {generation_time:.2f}s")
                
                # Step 2: 判别检查
                if self.enable_logging:
                    logger.debug(f"Evaluating output with critic...")
                
                critic_start = time.time()
                feedback = critic_func(output, context)
                critic_time = time.time() - critic_start
                
                # 确保 feedback 是 CriticFeedback 实例
                if not isinstance(feedback, CriticFeedback):
                    logger.error(f"Invalid feedback type: {type(feedback)}")
                    raise TypeError(
                        f"critic_func must return CriticFeedback, got {type(feedback)}"
                    )
                
                feedback_history.append(feedback)
                
                if self.enable_logging:
                    logger.debug(
                        f"Critic evaluation completed in {critic_time:.2f}s: "
                        f"approved={feedback.is_approved}, "
                        f"confidence={feedback.confidence_score:.2f}"
                    )
                
                # Step 3: 判断是否通过
                if feedback.is_approved:
                    self.successful_executions += 1
                    elapsed_time = time.time() - start_time
                    
                    if self.enable_logging:
                        logger.info(
                            f"✅ Verification passed on attempt {attempt + 1}/{total_attempts} "
                            f"(total time: {elapsed_time:.2f}s)"
                        )
                    
                    return output, feedback_history
                
                # 未通过，记录原因
                if self.enable_logging:
                    logger.warning(
                        f"❌ Attempt {attempt + 1}/{total_attempts} failed: "
                        f"{feedback.reasoning}"
                    )
                    if feedback.suggestion:
                        logger.info(f"💡 Suggestion: {feedback.suggestion}")
                
            except Exception as e:
                error_msg = f"Error in verification loop (attempt {attempt + 1}): {str(e)}"
                logger.error(error_msg)
                
                # 创建一个表示错误的反馈
                error_feedback = CriticFeedback(
                    is_approved=False,
                    reasoning=f"Exception occurred: {str(e)}",
                    suggestion="Check the generator or critic function for errors",
                    confidence_score=0.0
                )
                feedback_history.append(error_feedback)
                
                # 如果是最后一次尝试，抛出异常
                if attempt == total_attempts - 1:
                    raise
        
        # 所有尝试都失败
        self.failed_executions += 1
        elapsed_time = time.time() - start_time
        
        if self.enable_logging:
            logger.error(
                f"❌ Verification failed after {total_attempts} attempts "
                f"(total time: {elapsed_time:.2f}s)"
            )
        
        # 返回最后一次的输出（即使未通过验证）
        return output, feedback_history
    
    def get_statistics(self) -> dict:
        """
        获取统计信息
        
        Returns:
            包含执行统计的字典
        """
        success_rate = (
            self.successful_executions / self.total_executions
            if self.total_executions > 0
            else 0.0
        )
        
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": success_rate
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        
        if self.enable_logging:
            logger.info("Statistics reset")


class AdaptiveVerificationLoop(VerificationLoop):
    """
    自适应核验循环器
    
    增强功能：
    1. 根据历史通过率动态调整 max_retries
    2. 支持早停策略（连续多次失败后提前终止）
    3. 学习最优的 strictness_level
    
    适用场景：长期运行的系统，需要自动优化性能
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        strictness_level: float = 0.7,
        enable_logging: bool = True,
        adaptation_window: int = 100,
        min_retries: int = 1,
        max_max_retries: int = 10
    ):
        """
        初始化自适应核验循环器
        
        Args:
            max_retries: 初始最大重试次数
            strictness_level: 初始严格度等级
            enable_logging: 是否启用详细日志
            adaptation_window: 自适应窗口大小（多少次执行后重新评估）
            min_retries: 最小重试次数（自适应下限）
            max_max_retries: 最大重试次数的上限（自适应上限）
        """
        super().__init__(max_retries, strictness_level, enable_logging)
        
        self.adaptation_window = adaptation_window
        self.min_retries = min_retries
        self.max_max_retries = max_max_retries
        
        # 历史记录（用于自适应）
        self.recent_results: List[bool] = []  # True=成功, False=失败
        self.recent_attempts: List[int] = []  # 记录每次成功所需的尝试次数
    
    def execute(
        self,
        generator_func: Callable[[], BaseModel],
        critic_func: Callable[[BaseModel, Any], CriticFeedback],
        context: Any = None
    ) -> Tuple[BaseModel, List[CriticFeedback]]:
        """
        执行自适应核验循环
        """
        output, feedback_history = super().execute(generator_func, critic_func, context)
        
        # 记录结果
        is_successful = feedback_history[-1].is_approved if feedback_history else False
        self.recent_results.append(is_successful)
        self.recent_attempts.append(len(feedback_history))
        
        # 自适应调整
        if len(self.recent_results) >= self.adaptation_window:
            self._adapt_parameters()
        
        return output, feedback_history
    
    def _adapt_parameters(self):
        """
        根据历史数据自适应调整参数
        """
        if not self.recent_results:
            return
        
        # 计算最近的成功率
        recent_success_rate = sum(self.recent_results) / len(self.recent_results)
        
        # 计算平均尝试次数（仅统计成功的）
        successful_attempts = [
            attempts for success, attempts in zip(self.recent_results, self.recent_attempts)
            if success
        ]
        avg_attempts = (
            sum(successful_attempts) / len(successful_attempts)
            if successful_attempts else self.max_retries
        )
        
        # 调整策略
        old_max_retries = self.max_retries
        
        if recent_success_rate > 0.9:
            # 成功率很高，可以降低重试次数以提高效率
            self.max_retries = max(self.min_retries, self.max_retries - 1)
        elif recent_success_rate < 0.7:
            # 成功率较低，增加重试次数
            self.max_retries = min(self.max_max_retries, self.max_retries + 1)
        
        if old_max_retries != self.max_retries and self.enable_logging:
            logger.info(
                f"🔧 Adaptive adjustment: max_retries {old_max_retries} → {self.max_retries} "
                f"(success_rate={recent_success_rate:.2%}, avg_attempts={avg_attempts:.1f})"
            )
        
        # 清空历史（开始新的窗口）
        self.recent_results.clear()
        self.recent_attempts.clear()
