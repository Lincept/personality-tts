"""
简单测试脚本 - Phase 1 核验循环功能验证
不依赖 pytest，直接运行
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

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


# ==================== 测试函数 ====================

def test_basic_verification():
    """测试1：基础核验循环"""
    print("\n" + "="*70)
    print("测试1：基础核验循环 - 首次尝试即通过")
    print("="*70)
    
    loop = VerificationLoop(max_retries=3, enable_logging=False)
    
    # 定义生成器：产生高质量输出
    def generator():
        return MockAgentOutput(content="高质量输出", quality_score=0.9)
    
    # 定义判别器：评分 >= 0.7 即通过
    def critic(output: MockAgentOutput, context: Any) -> CriticFeedback:
        is_approved = output.quality_score >= 0.7
        return CriticFeedback(
            is_approved=is_approved,
            reasoning=f"质量评分 {output.quality_score}，{'通过' if is_approved else '未通过'}",
            confidence_score=0.9
        )
    
    result, feedback_history = loop.execute(generator, critic, context="测试输入")
    
    print(f"✓ 结果质量: {result.quality_score}")
    print(f"✓ 尝试次数: {len(feedback_history)}")
    print(f"✓ 最终通过: {feedback_history[-1].is_approved}")
    
    assert result.quality_score == 0.9
    assert len(feedback_history) == 1
    assert feedback_history[0].is_approved is True
    
    print("✅ 测试1通过！")
    return True


def test_retry_mechanism():
    """测试2：重试机制"""
    print("\n" + "="*70)
    print("测试2：重试机制 - 第二次尝试通过")
    print("="*70)
    
    loop = VerificationLoop(max_retries=3, enable_logging=False)
    
    # 模拟生成器：第一次质量低，第二次质量高
    attempt_count = [0]
    
    def generator():
        attempt_count[0] += 1
        quality = 0.6 if attempt_count[0] == 1 else 0.85
        print(f"  第 {attempt_count[0]} 次生成，质量评分: {quality}")
        return MockAgentOutput(content=f"尝试{attempt_count[0]}", quality_score=quality)
    
    def critic(output: MockAgentOutput, context: Any) -> CriticFeedback:
        is_approved = output.quality_score >= 0.7
        reasoning = f"质量评分 {output.quality_score}，{'通过' if is_approved else '未通过'}"
        print(f"  判别结果: {reasoning}")
        return CriticFeedback(
            is_approved=is_approved,
            reasoning=reasoning,
            suggestion="提高质量评分" if not is_approved else "",
            confidence_score=0.85
        )
    
    result, feedback_history = loop.execute(generator, critic, context="测试输入")
    
    print(f"\n✓ 总尝试次数: {len(feedback_history)}")
    print(f"✓ 第1次通过: {feedback_history[0].is_approved}")
    print(f"✓ 第2次通过: {feedback_history[1].is_approved}")
    print(f"✓ 最终质量: {result.quality_score}")
    
    assert len(feedback_history) == 2
    assert feedback_history[0].is_approved is False
    assert feedback_history[1].is_approved is True
    
    print("✅ 测试2通过！")
    return True


def test_max_retries():
    """测试3：达到最大重试次数"""
    print("\n" + "="*70)
    print("测试3：最大重试次数 - 用尽所有尝试")
    print("="*70)
    
    loop = VerificationLoop(max_retries=2, enable_logging=False)
    
    # 生成器：始终产生低质量输出
    def generator():
        return MockAgentOutput(content="低质量", quality_score=0.5)
    
    # 判别器：高标准（需要 >= 0.8）
    def critic(output: MockAgentOutput, context: Any) -> CriticFeedback:
        is_approved = output.quality_score >= 0.8
        return CriticFeedback(
            is_approved=is_approved,
            reasoning=f"质量 {output.quality_score} < 要求的 0.8",
            suggestion="需要显著提高质量",
            confidence_score=0.9
        )
    
    result, feedback_history = loop.execute(generator, critic, context="测试输入")
    
    print(f"✓ 尝试次数: {len(feedback_history)} (首次 + {loop.max_retries} 次重试)")
    print(f"✓ 所有尝试均未通过: {all(not fb.is_approved for fb in feedback_history)}")
    
    assert len(feedback_history) == 3  # 首次 + 2次重试
    assert all(not fb.is_approved for fb in feedback_history)
    
    print("✅ 测试3通过！")
    return True


def test_statistics():
    """测试4：统计信息"""
    print("\n" + "="*70)
    print("测试4：统计信息收集")
    print("="*70)
    
    loop = VerificationLoop(max_retries=2, enable_logging=False)
    
    # 第一次：成功
    def gen1():
        return MockAgentOutput(content="输出1", quality_score=0.9)
    
    def critic_pass(output, context):
        return CriticFeedback(is_approved=True, reasoning="通过", confidence_score=1.0)
    
    loop.execute(gen1, critic_pass, context="test1")
    
    # 第二次：失败
    def gen2():
        return MockAgentOutput(content="输出2", quality_score=0.5)
    
    def critic_fail(output, context):
        return CriticFeedback(is_approved=False, reasoning="未通过", confidence_score=0.9)
    
    loop.execute(gen2, critic_fail, context="test2")
    
    stats = loop.get_statistics()
    
    print(f"✓ 总执行次数: {stats['total_executions']}")
    print(f"✓ 成功次数: {stats['successful_executions']}")
    print(f"✓ 失败次数: {stats['failed_executions']}")
    print(f"✓ 成功率: {stats['success_rate']:.1%}")
    
    assert stats['total_executions'] == 2
    assert stats['successful_executions'] == 1
    assert stats['failed_executions'] == 1
    assert abs(stats['success_rate'] - 0.5) < 0.01
    
    print("✅ 测试4通过！")
    return True


def test_data_models():
    """测试5：新增数据模型"""
    print("\n" + "="*70)
    print("测试5：新增数据模型验证")
    print("="*70)
    
    from models.schemas import (
        RawReview,
        CriticFeedback,
        StructuredKnowledgeNode,
        SlangDecodingResult,
        WeightAnalysisResult,
        CompressionResult
    )
    
    # 测试 RawReview
    review = RawReview(
        content="这老板简直是'学术妲己'！",
        source_metadata={"platform": "知乎", "author_id": "user123"}
    )
    print(f"✓ RawReview: {review.content[:20]}...")
    
    # 测试 CriticFeedback
    feedback = CriticFeedback(
        is_approved=True,
        reasoning="输出质量良好",
        confidence_score=0.85
    )
    print(f"✓ CriticFeedback: approved={feedback.is_approved}, confidence={feedback.confidence_score}")
    
    # 测试 StructuredKnowledgeNode
    node = StructuredKnowledgeNode(
        mentor_id="mentor_001",
        dimension="Funding",
        fact_content="经费充足",
        weight_score=0.75,
        tags=["经费", "资源"]
    )
    print(f"✓ StructuredKnowledgeNode: {node.dimension}, weight={node.weight_score}")
    
    # 测试 SlangDecodingResult
    slang_result = SlangDecodingResult(
        decoded_text="导师很会承诺但不兑现",
        slang_dictionary={"学术妲己": "善于承诺但不兑现的导师"},
        confidence_score=0.9
    )
    print(f"✓ SlangDecodingResult: {len(slang_result.slang_dictionary)} 个黑话")
    
    # 测试 WeightAnalysisResult
    weight_result = WeightAnalysisResult(
        weight_score=0.78,
        identity_confidence=0.85,
        time_decay=0.9,
        outlier_status=False,
        reasoning="来源可信"
    )
    print(f"✓ WeightAnalysisResult: score={weight_result.weight_score}")
    
    # 测试 CompressionResult
    compression = CompressionResult(
        structured_node=node,
        compression_ratio=0.3
    )
    print(f"✓ CompressionResult: ratio={compression.compression_ratio}")
    
    print("✅ 测试5通过！所有数据模型正常工作")
    return True


def test_adaptive_loop():
    """测试6：自适应核验循环"""
    print("\n" + "="*70)
    print("测试6：自适应核验循环")
    print("="*70)
    
    loop = AdaptiveVerificationLoop(
        max_retries=3,
        adaptation_window=10,
        enable_logging=False
    )
    
    def generator():
        return MockAgentOutput(content="测试输出", quality_score=0.9)
    
    def critic(output, context):
        return CriticFeedback(is_approved=True, reasoning="通过", confidence_score=1.0)
    
    result, feedback = loop.execute(generator, critic, context="test")
    
    print(f"✓ 自适应循环执行成功")
    print(f"✓ 当前 max_retries: {loop.max_retries}")
    
    assert result.quality_score == 0.9
    print("✅ 测试6通过！")
    return True


# ==================== 主测试函数 ====================

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("Phase 1 核验循环机制 - 功能验证测试")
    print("="*70)
    
    tests = [
        ("基础核验循环", test_basic_verification),
        ("重试机制", test_retry_mechanism),
        ("最大重试次数", test_max_retries),
        ("统计信息", test_statistics),
        ("数据模型", test_data_models),
        ("自适应循环", test_adaptive_loop),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ 测试失败: {name}")
            print(f"   错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    print(f"✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Phase 1 核心功能实现成功！")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要修复")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
