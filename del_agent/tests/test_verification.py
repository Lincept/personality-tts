"""
Unit tests for Verification Loop - Phase 1
核验循环机制的单元测试
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from core.verification import VerificationLoop, AdaptiveVerificationLoop
from models.schemas import CriticFeedback


# ==================== 测试用数据模型 ====================

class MockAgentOutput(BaseModel):
    """模拟 Agent 输出"""
    content: str = Field(..., description="输出内容")
    quality_score: float = Field(default=0.5, description="质量评分")
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== 测试辅助函数 ====================

def create_generator(
    output_content: str = "test output",
    quality_score: float = 0.8,
    should_fail: bool = False
):
    """创建模拟的生成器函数"""
    def generator():
        if should_fail:
            raise ValueError("Generator failed intentionally")
        return MockAgentOutput(
            content=output_content,
            quality_score=quality_score
        )
    return generator


def create_critic(
    approval_threshold: float = 0.7,
    always_approve: bool = False,
    always_reject: bool = False
):
    """创建模拟的判别器函数"""
    def critic(output: MockAgentOutput, context: Any) -> CriticFeedback:
        if always_approve:
            return CriticFeedback(
                is_approved=True,
                reasoning="Approved by always_approve mode",
                confidence_score=1.0
            )
        
        if always_reject:
            return CriticFeedback(
                is_approved=False,
                reasoning="Rejected by always_reject mode",
                suggestion="Try improving the quality",
                confidence_score=0.9
            )
        
        # 根据质量评分判断
        is_approved = output.quality_score >= approval_threshold
        return CriticFeedback(
            is_approved=is_approved,
            reasoning=f"Quality score {output.quality_score} {'≥' if is_approved else '<'} threshold {approval_threshold}",
            suggestion="Increase quality score" if not is_approved else "",
            confidence_score=0.85
        )
    
    return critic


# ==================== 基础功能测试 ====================

def test_verification_loop_initialization():
    """测试：核验循环器初始化"""
    loop = VerificationLoop(max_retries=3, strictness_level=0.7)
    
    assert loop.max_retries == 3
    assert loop.strictness_level == 0.7
    assert loop.total_executions == 0
    assert loop.successful_executions == 0
    assert loop.failed_executions == 0


def test_verification_loop_invalid_params():
    """测试：无效参数应抛出异常"""
    with pytest.raises(ValueError):
        VerificationLoop(max_retries=-1)
    
    with pytest.raises(ValueError):
        VerificationLoop(strictness_level=1.5)


def test_successful_first_attempt():
    """测试：首次尝试即通过"""
    loop = VerificationLoop(max_retries=3)
    
    generator = create_generator(quality_score=0.9)
    critic = create_critic(approval_threshold=0.7)
    
    result, feedback_history = loop.execute(generator, critic, context="test")
    
    # 验证结果
    assert result.quality_score == 0.9
    assert len(feedback_history) == 1
    assert feedback_history[0].is_approved is True
    
    # 验证统计信息
    stats = loop.get_statistics()
    assert stats['total_executions'] == 1
    assert stats['successful_executions'] == 1
    assert stats['success_rate'] == 1.0


def test_retry_then_success():
    """测试：重试后成功"""
    loop = VerificationLoop(max_retries=3)
    
    # 创建一个会在第二次尝试时提高质量的生成器
    attempt_count = [0]
    
    def generator():
        attempt_count[0] += 1
        quality = 0.6 if attempt_count[0] == 1 else 0.9
        return MockAgentOutput(content=f"attempt_{attempt_count[0]}", quality_score=quality)
    
    critic = create_critic(approval_threshold=0.7)
    
    result, feedback_history = loop.execute(generator, critic, context="test")
    
    # 验证结果
    assert result.quality_score == 0.9
    assert len(feedback_history) == 2
    assert feedback_history[0].is_approved is False
    assert feedback_history[1].is_approved is True


def test_max_retries_exhausted():
    """测试：达到最大重试次数"""
    loop = VerificationLoop(max_retries=2, enable_logging=False)
    
    generator = create_generator(quality_score=0.5)  # 质量不足
    critic = create_critic(approval_threshold=0.8)   # 高阈值
    
    result, feedback_history = loop.execute(generator, critic, context="test")
    
    # 验证结果
    assert len(feedback_history) == 3  # 首次 + 2次重试
    assert all(not fb.is_approved for fb in feedback_history)
    
    # 验证统计信息
    stats = loop.get_statistics()
    assert stats['failed_executions'] == 1


def test_always_approve():
    """测试：总是通过的判别器"""
    loop = VerificationLoop(max_retries=3)
    
    generator = create_generator(quality_score=0.1)  # 极低质量
    critic = create_critic(always_approve=True)
    
    result, feedback_history = loop.execute(generator, critic, context="test")
    
    # 应该首次就通过
    assert len(feedback_history) == 1
    assert feedback_history[0].is_approved is True


def test_always_reject():
    """测试：总是拒绝的判别器"""
    loop = VerificationLoop(max_retries=2)
    
    generator = create_generator(quality_score=0.9)  # 高质量
    critic = create_critic(always_reject=True)
    
    result, feedback_history = loop.execute(generator, critic, context="test")
    
    # 应该用尽所有重试
    assert len(feedback_history) == 3  # 首次 + 2次重试
    assert all(not fb.is_approved for fb in feedback_history)


# ==================== 异常处理测试 ====================

def test_generator_exception():
    """测试：生成器抛出异常"""
    loop = VerificationLoop(max_retries=1)
    
    generator = create_generator(should_fail=True)
    critic = create_critic()
    
    with pytest.raises(ValueError, match="Generator failed intentionally"):
        loop.execute(generator, critic, context="test")


def test_critic_exception():
    """测试：判别器抛出异常"""
    loop = VerificationLoop(max_retries=1)
    
    generator = create_generator()
    
    def bad_critic(output, context):
        raise RuntimeError("Critic failed")
    
    with pytest.raises(RuntimeError, match="Critic failed"):
        loop.execute(generator, bad_critic, context="test")


def test_invalid_feedback_type():
    """测试：判别器返回错误类型"""
    loop = VerificationLoop(max_retries=1)
    
    generator = create_generator()
    
    def bad_critic(output, context):
        return "not a CriticFeedback"  # 错误类型
    
    with pytest.raises(TypeError, match="must return CriticFeedback"):
        loop.execute(generator, bad_critic, context="test")


# ==================== 统计功能测试 ====================

def test_statistics_multiple_executions():
    """测试：多次执行后的统计信息"""
    loop = VerificationLoop(max_retries=2)
    
    # 第一次：成功
    generator1 = create_generator(quality_score=0.9)
    critic1 = create_critic(approval_threshold=0.7)
    loop.execute(generator1, critic1, context="test1")
    
    # 第二次：失败
    generator2 = create_generator(quality_score=0.5)
    critic2 = create_critic(approval_threshold=0.8)
    loop.execute(generator2, critic2, context="test2")
    
    # 第三次：成功
    generator3 = create_generator(quality_score=0.95)
    critic3 = create_critic(approval_threshold=0.7)
    loop.execute(generator3, critic3, context="test3")
    
    # 验证统计
    stats = loop.get_statistics()
    assert stats['total_executions'] == 3
    assert stats['successful_executions'] == 2
    assert stats['failed_executions'] == 1
    assert abs(stats['success_rate'] - 2/3) < 0.01


def test_reset_statistics():
    """测试：重置统计信息"""
    loop = VerificationLoop(max_retries=2)
    
    generator = create_generator()
    critic = create_critic(always_approve=True)
    loop.execute(generator, critic, context="test")
    
    assert loop.total_executions == 1
    
    loop.reset_statistics()
    
    assert loop.total_executions == 0
    assert loop.successful_executions == 0
    assert loop.failed_executions == 0


# ==================== 自适应核验循环测试 ====================

def test_adaptive_loop_initialization():
    """测试：自适应循环器初始化"""
    loop = AdaptiveVerificationLoop(
        max_retries=3,
        adaptation_window=100,
        min_retries=1,
        max_max_retries=10
    )
    
    assert loop.max_retries == 3
    assert loop.adaptation_window == 100
    assert loop.min_retries == 1
    assert loop.max_max_retries == 10


def test_adaptive_loop_basic_execution():
    """测试：自适应循环器基本执行"""
    loop = AdaptiveVerificationLoop(max_retries=3)
    
    generator = create_generator(quality_score=0.9)
    critic = create_critic(approval_threshold=0.7)
    
    result, feedback_history = loop.execute(generator, critic, context="test")
    
    assert result.quality_score == 0.9
    assert len(feedback_history) == 1


# ==================== 集成测试 ====================

def test_feedback_history_content():
    """测试：反馈历史内容完整性"""
    loop = VerificationLoop(max_retries=2)
    
    attempt_count = [0]
    
    def generator():
        attempt_count[0] += 1
        return MockAgentOutput(
            content=f"attempt_{attempt_count[0]}",
            quality_score=0.6 + attempt_count[0] * 0.1
        )
    
    critic = create_critic(approval_threshold=0.75)
    
    result, feedback_history = loop.execute(generator, critic, context="original_input")
    
    # 验证反馈历史
    assert len(feedback_history) == 2  # 第1次失败，第2次成功
    
    # 第1次反馈
    assert feedback_history[0].is_approved is False
    assert "0.7" in feedback_history[0].reasoning
    assert feedback_history[0].suggestion != ""
    
    # 第2次反馈
    assert feedback_history[1].is_approved is True
    assert "0.8" in feedback_history[1].reasoning


# ==================== 运行测试 ====================

if __name__ == "__main__":
    print("=" * 70)
    print("Running Verification Loop Unit Tests - Phase 1")
    print("=" * 70)
    
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
