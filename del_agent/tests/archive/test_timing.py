#!/usr/bin/env python3
"""
测试Pipeline性能计时功能
展示每个步骤的详细耗时统计
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 确保正确导入
from core.llm_adapter import OpenAICompatibleProvider
from backend.factory import DataFactoryPipeline
from models.schemas import RawReview


def print_separator(char="=", length=80):
    """打印分隔符"""
    print(char * length)


def main():
    """主测试函数"""
    print_separator()
    print("  Pipeline 性能计时测试")
    print_separator()
    print()
    
    # 从环境变量获取API Key
    api_key = os.getenv('ARK_API_KEY')
    
    if not api_key:
        logger.error("请设置 ARK_API_KEY 环境变量")
        return False
    
    # 创建LLM提供者（豆包）
    llm_provider = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60,
        reasoning_effort="minimal"
    )
    logger.info("✓ LLM Provider initialized")
    
    # 创建Pipeline
    pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=False
    )
    logger.info("✓ Pipeline initialized")
    
    # 创建测试评论
    test_review = RawReview(
        review_id="test_001",
        content="这老板简直是'学术妲己'，太会画饼了！经费倒是多，但不发给我们。实验室设备老旧，申请新设备总是拖延。",
        author_id="test_author",
        mentor_id="mentor_zhang",
        timestamp=datetime.now(),
        source_platform="test",
        source_metadata={"platform": "test", "rating": 3}
    )
    
    print("\n测试评论:")
    print(f"  {test_review.content}")
    print()
    print_separator("-")
    print("开始处理...\n")
    
    # 处理评论
    try:
        result = pipeline.process_raw_review(test_review)
        
        print()
        print_separator("-")
        print("\n✅ 处理成功！")
        print(f"\n结果:")
        print(f"  - 导师ID: {result.mentor_id}")
        print(f"  - 维度: {result.dimension}")
        print(f"  - 事实内容: {result.fact_content}")
        print(f"  - 权重评分: {result.weight_score:.2f}")
        print(f"  - 标签: {', '.join(result.tags)}")
        
    except Exception as e:
        logger.error(f"❌ 处理失败: {str(e)}", exc_info=True)
        return False
    
    print()
    print_separator()
    print("💡 提示: 查看上方日志可以看到每个步骤的详细耗时统计")
    print_separator()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
