"""
Phase 1 演示脚本 - 核验循环机制
展示如何在实际场景中使用 Verification Loop
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.verification import VerificationLoop, AdaptiveVerificationLoop
from models.schemas import CriticFeedback, CommentCleaningResult
from pydantic import BaseModel, Field
from typing import Dict, Any


def demo_basic_verification():
    """演示1：基础核验循环"""
    print("\n" + "="*70)
    print("演示1：基础核验循环 - 评论清洗质量检查")
    print("="*70)
    
    # 模拟一个评论清洗 Agent 的输出
    class CleanerOutput(BaseModel):
        factual_content: str
        quality: float
        metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 创建核验循环器
    loop = VerificationLoop(max_retries=3, strictness_level=0.7)
    
    # 模拟生成器（实际场景中这会是 RawCommentCleaner.process()）
    raw_comment = "这老板简直是'学术妲己'，太会画饼了！经费倒是多，但不发给我们。"
    
    attempt_count = [0]
    
    def cleaner_generator():
        attempt_count[0] += 1
        print(f"\n📝 第 {attempt_count[0]} 次处理...")
        
        # 第一次：提取不够完整
        if attempt_count[0] == 1:
            return CleanerOutput(
                factual_content="经费多",
                quality=0.6
            )
        # 第二次：提取更完整
        else:
            return CleanerOutput(
                factual_content="经费充足，但学生津贴发放少",
                quality=0.85
            )
    
    # 模拟判别器（实际场景中这会是 CriticAgent.evaluate()）
    def quality_critic(output: CleanerOutput, context: Any) -> CriticFeedback:
        is_approved = output.quality >= 0.7
        
        if is_approved:
            reasoning = f"✅ 内容质量良好（{output.quality:.2f}），事实提取完整"
        else:
            reasoning = f"❌ 内容质量不足（{output.quality:.2f}），事实提取不够详细"
        
        print(f"🔍 判别: {reasoning}")
        
        return CriticFeedback(
            is_approved=is_approved,
            reasoning=reasoning,
            suggestion="需要提取更多关键事实信息" if not is_approved else "",
            confidence_score=0.9
        )
    
    # 执行核验循环
    print(f"原始评论: {raw_comment}")
    result, feedback_history = loop.execute(
        cleaner_generator,
        quality_critic,
        context=raw_comment
    )
    
    # 显示结果
    print(f"\n📊 核验结果:")
    print(f"  - 总尝试次数: {len(feedback_history)}")
    print(f"  - 最终内容: {result.factual_content}")
    print(f"  - 质量评分: {result.quality}")
    print(f"  - 是否通过: {feedback_history[-1].is_approved}")
    
    # 显示反馈历史
    print(f"\n📜 反馈历史:")
    for i, feedback in enumerate(feedback_history, 1):
        print(f"  第{i}次: {'✅ 通过' if feedback.is_approved else '❌ 未通过'} - {feedback.reasoning}")


def demo_with_real_agent():
    """演示2：与真实 Agent 集成"""
    print("\n" + "="*70)
    print("演示2：与 RawCommentCleaner 集成使用")
    print("="*70)
    
    # 注意：这需要 LLM API 配置
    print("\n⚠️  此演示需要配置 LLM API（跳过实际调用）")
    print("集成方式示例：")
    
    code_example = '''
    from core.llm_adapter import OpenAICompatibleProvider
    from agents.raw_comment_cleaner import RawCommentCleaner
    from agents.critic import CriticAgent  # Phase 2 将实现
    
    # 创建 LLM 提供者
    llm_provider = OpenAICompatibleProvider(
        model_name="deepseek-chat",
        api_key="your-api-key",
        base_url="https://api.deepseek.com"
    )
    
    # 创建智能体
    cleaner = RawCommentCleaner(llm_provider)
    critic = CriticAgent(llm_provider, strictness_level=0.7)
    
    # 使用核验循环处理
    result = cleaner.process_with_verification(
        raw_input="这老板简直是'学术妲己'！",
        critic_agent=critic,
        max_retries=3
    )
    
    # 查看反馈历史
    print(result.metadata['feedback_history'])
    print(result.metadata['verification_stats'])
    '''
    
    print(code_example)


def demo_adaptive_loop():
    """演示3：自适应核验循环"""
    print("\n" + "="*70)
    print("演示3：自适应核验循环 - 自动优化重试次数")
    print("="*70)
    
    # 创建自适应循环器
    loop = AdaptiveVerificationLoop(
        max_retries=5,
        adaptation_window=10,  # 每10次执行后重新评估
        min_retries=1,
        max_max_retries=10
    )
    
    print(f"初始 max_retries: {loop.max_retries}")
    
    # 模拟多次执行
    print("\n模拟处理100条评论...")
    
    class SimpleOutput(BaseModel):
        content: str
        quality: float
        metadata: Dict[str, Any] = Field(default_factory=dict)
    
    success_count = 0
    
    for i in range(100):
        # 80% 的情况下首次即成功
        quality = 0.85 if i % 5 != 0 else 0.65
        
        def generator():
            return SimpleOutput(content=f"output_{i}", quality=quality)
        
        def critic(output, context):
            is_approved = output.quality >= 0.7
            return CriticFeedback(
                is_approved=is_approved,
                reasoning="通过" if is_approved else "未通过",
                confidence_score=0.9
            )
        
        result, _ = loop.execute(generator, critic, context=f"input_{i}")
        if result.quality >= 0.7:
            success_count += 1
        
        # 每10次显示一次状态
        if (i + 1) % 10 == 0:
            stats = loop.get_statistics()
            print(f"  处理 {i+1}/100 条 | "
                  f"当前 max_retries={loop.max_retries} | "
                  f"成功率={stats['success_rate']:.1%}")
    
    # 最终统计
    final_stats = loop.get_statistics()
    print(f"\n📊 最终统计:")
    print(f"  - 总处理数: {final_stats['total_executions']}")
    print(f"  - 成功数: {final_stats['successful_executions']}")
    print(f"  - 成功率: {final_stats['success_rate']:.1%}")
    print(f"  - 最终 max_retries: {loop.max_retries}")
    print(f"  - 优化说明: 由于成功率高，系统自动降低了重试次数以提高效率")


def demo_statistics():
    """演示4：统计信息收集"""
    print("\n" + "="*70)
    print("演示4：统计信息收集与分析")
    print("="*70)
    
    loop = VerificationLoop(max_retries=3, enable_logging=False)
    
    class Output(BaseModel):
        value: int
        metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 模拟不同场景
    scenarios = [
        ("高质量输入", 0.95, True),
        ("中等质量", 0.75, True),
        ("低质量输入", 0.45, False),
        ("高质量输入", 0.90, True),
        ("极低质量", 0.30, False),
    ]
    
    print("\n处理不同质量的输入...")
    for name, quality, expected_pass in scenarios:
        def gen():
            return Output(value=int(quality * 100))
        
        def critic(output, context):
            is_approved = output.value >= 70
            return CriticFeedback(
                is_approved=is_approved,
                reasoning=f"值为 {output.value}",
                confidence_score=0.9
            )
        
        result, history = loop.execute(gen, critic, context=name)
        status = "✅" if history[-1].is_approved else "❌"
        print(f"  {status} {name}: 值={result.value}, 尝试={len(history)}次")
    
    # 显示统计
    stats = loop.get_statistics()
    print(f"\n📊 汇总统计:")
    print(f"  - 总执行: {stats['total_executions']} 次")
    print(f"  - 成功: {stats['successful_executions']} 次")
    print(f"  - 失败: {stats['failed_executions']} 次")
    print(f"  - 成功率: {stats['success_rate']:.1%}")


def main():
    """主函数"""
    print("="*70)
    print("Phase 1 核验循环机制 - 功能演示")
    print("="*70)
    
    demos = [
        demo_basic_verification,
        demo_with_real_agent,
        demo_adaptive_loop,
        demo_statistics
    ]
    
    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ 演示出错: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("演示完成！")
    print("="*70)
    print("\n💡 关键要点:")
    print("  1. VerificationLoop 实现了 Agent Output → Critic Check → Pass/Retry 循环")
    print("  2. 可以轻松集成到任何继承自 BaseAgent 的智能体中")
    print("  3. 通过 process_with_verification() 方法使用")
    print("  4. 反馈历史保存在结果的 metadata 中")
    print("  5. AdaptiveVerificationLoop 可以自动优化重试次数")
    print("\n📚 下一步: Phase 2 - 实现 CriticAgent 和其他后端智能体")


if __name__ == "__main__":
    main()
