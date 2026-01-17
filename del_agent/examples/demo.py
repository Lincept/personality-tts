# AI Data Factory 演示脚本
"""
演示如何使用RawCommentCleaner智能体处理原始评论数据
"""

import os
import sys
import logging
from pathlib import Path

# 将项目根目录添加到Python路径
# 获取项目根目录的路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent  # Go up two levels from examples directory
sys.path.insert(0, str(project_root))

from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.agents.raw_comment_cleaner import RawCommentCleaner
from del_agent.utils.config import get_config_manager
from del_agent.core.prompt_manager import get_default_prompt_manager


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_demo_comments():
    """创建演示用的评论数据"""
    return [
        "这老板简直是'学术妲己'，太会画饼了！经费倒是多，但不发给我们。",
        "实验室氛围还行，师兄师姐都挺友好的，就是设备有点老旧。",
        "导师人很好，指导很耐心，就是项目进度有点慢，希望能加快点。",
        "这个课题组简直是地狱！天天加班到深夜，周末还要来实验室！",
        "研究方向挺前沿的，就是发表论文的压力有点大，需要努力。",
        "老板抠门得要死，出差补贴都不给，还让我们自己垫钱！",
        "实验室条件不错，新买了几台高端设备，用起来很顺手。",
        "导师经常不在实验室，指导不够，很多事情都要自己摸索。",
        "组里同学关系很好，经常一起聚餐，学习氛围也不错。",
        "这个方向太冷门了，找工作的时候会很困难，建议换个方向。"
    ]


def main():
    """主函数"""
    print("=== AI Data Factory - Raw Comment Cleaner Demo ===\n")
    
    # 设置日志
    setup_logging()
    
    # 获取配置管理器
    config_manager = get_config_manager()
    
    # 获取默认智能体配置
    default_agent_config = config_manager.get_agent_config("comment_cleaner")
    
    # 获取当前使用的LLM配置
    current_llm_provider = default_agent_config.llm_config.provider
    
    # 根据LLM提供者获取相应的API密钥
    if current_llm_provider == 'doubao':
        api_key = os.getenv('DOBAO_API_KEY')
        api_secret = os.getenv('DOBAO_API_SECRET')
        if not api_key or not api_secret:
            print("错误：请设置 DOBAO_API_KEY 和 DOBAO_API_SECRET 环境变量")
            print("示例：export DOBAO_API_KEY='your-api-key' DOBAO_API_SECRET='your-api-secret'")
            return
    elif current_llm_provider == 'qwen':
        api_key = os.getenv('QWEN_API_KEY')
        if not api_key:
            print("错误：请设置 QWEN_API_KEY 环境变量")
            print("示例：export QWEN_API_KEY='your-api-key'")
            return
    elif current_llm_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("错误：请设置 OPENAI_API_KEY 环境变量")
            print("示例：export OPENAI_API_KEY='your-api-key'")
            return
    elif current_llm_provider == 'deepseek':
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            print("错误：请设置 DEEPSEEK_API_KEY 环境变量")
            print("示例：export DEEPSEEK_API_KEY='your-api-key'")
            return
    elif current_llm_provider == 'moonshot':
        api_key = os.getenv('MOONSHOT_API_KEY')
        if not api_key:
            print("错误：请设置 MOONSHOT_API_KEY 环境变量")
            print("示例：export MOONSHOT_API_KEY='your-api-key'")
            return
    else:
        api_key = os.getenv('LLM_API_KEY')
        if not api_key:
            print(f"错误：请设置 LLM_API_KEY 环境变量（用于 {current_llm_provider}）")
            print("示例：export LLM_API_KEY='your-api-key'")
            return
    
    print(f"使用API密钥 (来自 {current_llm_provider}): {api_key[:10]}...")
    
    # 创建LLM提供者
    print("\n1. 创建LLM提供者...")
    
    # 获取LLM配置
    llm_config = default_agent_config.llm_config
    
    # 创建LLM提供者实例
    if current_llm_provider == 'doubao':
        llm_provider = OpenAICompatibleProvider(
            model_name=llm_config.model_name,
            api_key=api_key,
            api_secret=api_secret,
            base_url=llm_config.base_url,
            temperature=llm_config.temperature
        )
    else:
        llm_provider = OpenAICompatibleProvider(
            model_name=llm_config.model_name,
            api_key=api_key,
            base_url=llm_config.base_url,
            temperature=llm_config.temperature
        )
    print("✓ LLM提供者创建成功")
    
    # 创建评论清洗智能体
    print("\n2. 创建RawCommentCleaner智能体...")
    agent = RawCommentCleaner(
        llm_provider=llm_provider,
        prompt_manager=get_default_prompt_manager()
    )
    print("✓ 智能体创建成功")
    
    # 获取演示数据
    print("\n3. 准备演示数据...")
    demo_comments = create_demo_comments()
    print(f"✓ 准备了 {len(demo_comments)} 条演示评论")
    
    # 显示原始评论
    print("\n=== 原始评论数据 ===")
    for i, comment in enumerate(demo_comments, 1):
        print(f"{i}. {comment}")
    
    # 批量处理评论
    print("\n=== 开始批量处理 ===")
    results = agent.analyze_batch(demo_comments)
    
    # 显示处理结果
    print("\n=== 处理结果 ===")
    for i, (comment, result) in enumerate(zip(demo_comments, results), 1):
        print(f"\n评论 {i}:")
        print(f"原始: {comment}")
        print(f"事实内容: {result.factual_content}")
        print(f"情绪强度: {result.emotional_intensity:.2f}")
        print(f"关键词: {', '.join(result.keywords)}")
        print(f"状态: {'✓ 成功' if result.success else '✗ 失败'}")
        if result.error_message:
            print(f"错误: {result.error_message}")
    
    # 获取统计汇总
    print("\n=== 处理统计 ===")
    summary = agent.get_processing_summary(results)
    print(f"总计: {summary['total']} 条")
    print(f"成功: {summary['successful']} 条")
    print(f"失败: {summary['failed']} 条")
    print(f"成功率: {summary['success_rate']:.1%}")
    print(f"平均情绪强度: {summary['avg_emotional_intensity']:.2f}")
    print(f"唯一关键词数: {summary['unique_keywords']}")
    
    if summary['top_keywords']:
        print("\n热门关键词:")
        for keyword, count in summary['top_keywords']:
            print(f"  - {keyword}: {count} 次")
    
    # 显示智能体统计
    print("\n=== 智能体统计 ===")
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    main()