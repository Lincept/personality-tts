"""
完整的数据工厂流水线测试 - 展示 del_agent 核心功能
这个测试模拟真实用户使用场景，展示从原始评论到结构化知识节点的完整处理流程
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from core.llm_adapter import OpenAICompatibleProvider
from backend.factory import DataFactoryPipeline
from models.schemas import RawReview

# 加载环境变量
load_dotenv()


def print_separator(title: str = "", width: int = 80):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * width}")
        print(f" {title}")
        print(f"{'=' * width}")
    else:
        print("-" * width)


def format_json(obj, indent: int = 2) -> str:
    """格式化对象为JSON字符串"""
    if hasattr(obj, 'model_dump'):
        return json.dumps(obj.model_dump(), ensure_ascii=False, indent=indent)
    return json.dumps(obj, ensure_ascii=False, indent=indent)


def main():
    print_separator("del_agent 数据工厂完整流水线测试", 100)
    
    # 1. 配置 LLM 提供者
    print("\n📋 步骤 1: 配置 LLM 提供者")
    print_separator("", 100)
    
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        print("❌ 错误: 未找到 ARK_API_KEY 环境变量")
        return
    
    print(f"✓ 使用豆包模型")
    print(f"✓ API Key: {api_key[:15]}...")
    
    llm_provider = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60
    )
    print("✓ LLM 提供者创建成功")
    
    # 2. 初始化数据工厂流水线
    print_separator("步骤 2: 初始化数据工厂流水线", 100)
    
    pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=False,  # 先不启用核验，提高速度
        slang_dict_storage="json",
        slang_dict_path="./slang_dictionary.json"
    )
    print("✓ 数据工厂流水线初始化完成")
    print("  包含智能体: RawCommentCleaner → SlangDecoder → Weigher → Compressor")
    
    # 3. 准备测试数据
    print_separator("步骤 3: 准备测试数据", 100)
    
    test_reviews = [
        {
            "content": "这老板简直是'学术妲己'，太会画饼了！经费倒是多，但津贴不发给我们。",
            "metadata": {
                "platform": "知乎",
                "author_id": "student_001",
                "author_role": "博士生",
                "post_time": "2025-12-01"
            }
        },
        {
            "content": "导师人很nice，科研经费给的很足，实验设备也很先进，就是经常'放羊'，不怎么指导。",
            "metadata": {
                "platform": "小木虫",
                "author_id": "student_002",
                "author_role": "硕士生",
                "post_time": "2025-11-20"
            }
        },
        {
            "content": "导师学术水平很高，在领域内很有影响力，但是对学生要求太严格了，压力山大。",
            "metadata": {
                "platform": "豆瓣",
                "author_id": "student_003",
                "author_role": "博士生",
                "post_time": "2025-10-15"
            }
        }
    ]
    
    print(f"✓ 准备了 {len(test_reviews)} 条测试评论")
    for i, review in enumerate(test_reviews, 1):
        print(f"\n  评论 {i}:")
        print(f"    内容: {review['content'][:50]}...")
        print(f"    来源: {review['metadata']['platform']}")
        print(f"    作者角色: {review['metadata']['author_role']}")
    
    # 4. 批量处理评论
    print_separator("步骤 4: 批量处理评论", 100)
    print("开始处理流水线...\n")
    
    raw_reviews = []
    for review_data in test_reviews:
        raw_review = RawReview(
            content=review_data["content"],
            source_metadata=review_data["metadata"]
        )
        raw_reviews.append(raw_review)
    
    # 使用流水线批量处理
    knowledge_nodes = pipeline.process_batch(raw_reviews)
    
    # 5. 展示处理结果
    print_separator("步骤 5: 处理结果展示", 100)
    
    for i, node in enumerate(knowledge_nodes, 1):
        print(f"\n{'▼' * 50}")
        print(f"评论 {i} 处理结果:")
        print(f"{'▼' * 50}")
        
        print(f"✓ 处理成功")
        
        # 展示知识节点
        print(f"\n【知识节点】")
        print(f"  导师ID: {node.mentor_id}")
        print(f"  评价维度: {node.dimension}")
        print(f"  综合权重: {node.weight_score:.3f}")
        
        # 事实内容
        print(f"\n  事实内容:")
        print(f"    {node.fact_content}")
        
        # 原文特色
        if node.original_nuance:
            print(f"\n  原文特色/黑话:")
            print(f"    {node.original_nuance}")
        
        # 标签
        if node.tags:
            print(f"\n  标签: {', '.join(node.tags)}")
        
        # 元数据
        print(f"\n  更新时间: {node.last_updated}")
    
    # 6. 统计信息
    print_separator("步骤 6: 统计信息", 100)
    
    stats = pipeline.get_statistics()
    print(f"\n处理统计:")
    print(f"  总处理数: {stats['total_processed']}")
    print(f"  成功数: {stats['successful']}")
    print(f"  失败数: {stats['failed']}")
    print(f"  成功率: {stats.get('success_rate', 0) * 100:.1f}%")
    
    # 7. 保存结果
    print_separator("步骤 7: 保存结果", 100)
    
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_results_{timestamp}.json"
    
    # 将结果转换为可序列化的格式
    output_data = {
        "test_time": timestamp,
        "config": {
            "enable_verification": False,
            "model": "doubao-seed-1-6-251015"
        },
        "results": []
    }
    
    for i, node in enumerate(knowledge_nodes):
        result_data = {
            "review_index": i + 1,
            "original_content": test_reviews[i]["content"],
            "success": True,
            "knowledge_node": {
                **node.model_dump(),
                # 转换 datetime 为字符串
                "last_updated": node.last_updated.isoformat() if hasattr(node.last_updated, 'isoformat') else str(node.last_updated)
            }
        }
        
        output_data["results"].append(result_data)
    
    output_data["statistics"] = stats
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 结果已保存到: {output_file}")
    
    # 8. 测试核验循环（可选）
    print_separator("步骤 8: 测试核验循环功能（可选）", 100)
    
    print("\n是否要测试核验循环功能? (会增加处理时间)")
    print("核验循环会使用 CriticAgent 对结果进行质量评估和改进")
    print("本次测试跳过核验循环以加快速度")
    print("如需测试，请设置 enable_verification=True")
    
    print_separator("测试完成!", 100)
    print("\n✨ del_agent 数据工厂核心功能演示完毕")
    print("✨ 从原始评论 → 清洗 → 黑话解码 → 权重分析 → 结构化压缩 → 知识节点")
    print(f"✨ 查看详细结果: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")
    except Exception as e:
        print(f"\n\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
