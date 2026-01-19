"""
测试数据工厂流水线 (DataFactoryPipeline)
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from core.llm_adapter import LLMProvider
from models.schemas import RawReview
from backend.factory import DataFactoryPipeline
from utils.config import ConfigManager


def test_single_review():
    """测试单条评论处理"""
    print("=" * 80)
    print("测试1: 处理单条评论")
    print("=" * 80)
    
    # 加载配置
    config_manager = ConfigManager()
    llm_config = config_manager.get_llm_config("deepseek")
    
    # 创建LLM提供者
    llm_provider = LLMProvider(llm_config)
    
    # 创建数据工厂流水线（不启用核验循环以加快测试）
    pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=False
    )
    
    # 创建测试数据
    raw_review = RawReview(
        content="这个老板简直是'学术妲己'，天天画饼！说好的经费充足，结果学生津贴发得少得可怜。",
        source_metadata={
            "platform": "知乎",
            "author_id": "user_12345",
            "post_id": "post_67890",
            "verified": True,
            "identity": "student",
            "post_count": 150,
            "reputation": 800,
            "mentor_name": "Zhang San"
        },
        timestamp=datetime.now()
    )
    
    print(f"\n原始评论: {raw_review.content}")
    print(f"来源平台: {raw_review.source_metadata.get('platform')}")
    
    try:
        # 处理评论
        knowledge_node = pipeline.process_raw_review(raw_review)
        
        print("\n" + "=" * 80)
        print("✅ 处理成功！结构化知识节点：")
        print("=" * 80)
        print(f"导师ID: {knowledge_node.mentor_id}")
        print(f"维度: {knowledge_node.dimension}")
        print(f"事实内容: {knowledge_node.fact_content}")
        print(f"原文特色: {knowledge_node.original_nuance}")
        print(f"权重评分: {knowledge_node.weight_score:.2f}")
        print(f"标签: {', '.join(knowledge_node.tags)}")
        print(f"更新时间: {knowledge_node.last_updated}")
        
        # 显示统计信息
        stats = pipeline.get_statistics()
        print("\n" + "=" * 80)
        print("统计信息：")
        print("=" * 80)
        print(f"总处理数: {stats['total_processed']}")
        print(f"成功数: {stats['successful']}")
        print(f"失败数: {stats['failed']}")
        print(f"成功率: {stats['success_rate']:.1%}")
        
    except Exception as e:
        print(f"\n❌ 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_batch_reviews():
    """测试批量评论处理"""
    print("\n" + "=" * 80)
    print("测试2: 批量处理评论")
    print("=" * 80)
    
    # 加载配置
    config_manager = ConfigManager()
    llm_config = config_manager.get_llm_config("deepseek")
    
    # 创建LLM提供者
    llm_provider = LLMProvider(llm_config)
    
    # 创建数据工厂流水线
    pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=False
    )
    
    # 创建测试数据
    raw_reviews = [
        RawReview(
            content="导师人很好，但实验室设备老旧，经费不足。",
            source_metadata={
                "platform": "小木虫",
                "verified": True,
                "identity": "student",
                "post_count": 50,
                "reputation": 300,
                "mentor_name": "Li Si"
            },
            timestamp=datetime.now()
        ),
        RawReview(
            content="压力超级大，天天加班到深夜，但是能学到很多东西。",
            source_metadata={
                "platform": "知乎",
                "verified": False,
                "identity": "alumni",
                "post_count": 20,
                "reputation": 100,
                "mentor_name": "Wang Wu"
            },
            timestamp=datetime.now()
        ),
        RawReview(
            content="老板发Paper超快，但对学生要求也很严格，适合想冲一流期刊的同学。",
            source_metadata={
                "platform": "学术论坛",
                "verified": True,
                "identity": "student",
                "post_count": 100,
                "reputation": 600,
                "mentor_name": "Zhao Liu"
            },
            timestamp=datetime.now()
        )
    ]
    
    print(f"\n待处理评论数: {len(raw_reviews)}")
    for i, review in enumerate(raw_reviews, 1):
        print(f"{i}. {review.content[:30]}...")
    
    try:
        # 批量处理
        knowledge_nodes = pipeline.process_batch(raw_reviews)
        
        print("\n" + "=" * 80)
        print(f"✅ 批量处理完成！共生成 {len(knowledge_nodes)} 个知识节点")
        print("=" * 80)
        
        for i, node in enumerate(knowledge_nodes, 1):
            print(f"\n节点 {i}:")
            print(f"  导师ID: {node.mentor_id}")
            print(f"  维度: {node.dimension}")
            print(f"  权重: {node.weight_score:.2f}")
            print(f"  标签: {', '.join(node.tags)}")
        
        # 显示统计信息
        stats = pipeline.get_statistics()
        print("\n" + "=" * 80)
        print("统计信息：")
        print("=" * 80)
        print(f"总处理数: {stats['total_processed']}")
        print(f"成功数: {stats['successful']}")
        print(f"失败数: {stats['failed']}")
        print(f"成功率: {stats['success_rate']:.1%}")
        
    except Exception as e:
        print(f"\n❌ 批量处理失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_with_verification():
    """测试启用核验循环的流水线"""
    print("\n" + "=" * 80)
    print("测试3: 启用核验循环的流水线")
    print("=" * 80)
    
    # 加载配置
    config_manager = ConfigManager()
    llm_config = config_manager.get_llm_config("deepseek")
    
    # 创建LLM提供者
    llm_provider = LLMProvider(llm_config)
    
    # 创建数据工厂流水线（启用核验循环）
    pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=True,
        max_retries=2,
        strictness_level=0.7
    )
    
    # 创建测试数据
    raw_review = RawReview(
        content="导师是学术大牛，但对学生很严格，适合有自驱力的同学。",
        source_metadata={
            "platform": "知乎",
            "verified": True,
            "identity": "alumni",
            "post_count": 200,
            "reputation": 1200,
            "mentor_name": "Chen Qi"
        },
        timestamp=datetime.now()
    )
    
    print(f"\n原始评论: {raw_review.content}")
    print("启用核验循环（严格度: 0.7，最大重试: 2次）")
    
    try:
        # 处理评论
        knowledge_node = pipeline.process_raw_review(raw_review)
        
        print("\n" + "=" * 80)
        print("✅ 处理成功！")
        print("=" * 80)
        print(f"导师ID: {knowledge_node.mentor_id}")
        print(f"维度: {knowledge_node.dimension}")
        print(f"权重评分: {knowledge_node.weight_score:.2f}")
        
        # 显示统计信息
        stats = pipeline.get_statistics()
        print("\n统计信息：")
        print(f"核验通过次数: {stats['verification_passes']}")
        print(f"核验失败次数: {stats['verification_failures']}")
        
    except Exception as e:
        print(f"\n❌ 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行测试
    test_single_review()
    test_batch_reviews()
    test_with_verification()
    
    print("\n" + "=" * 80)
    print("🎉 所有测试完成！")
    print("=" * 80)
