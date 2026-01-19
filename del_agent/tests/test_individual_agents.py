"""
单个智能体功能测试 - 展示如何使用 del_agent 的各个智能体
这个测试展示如何像真实用户一样调用每个智能体
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from core.llm_adapter import OpenAICompatibleProvider
from agents.raw_comment_cleaner import RawCommentCleaner
from agents.slang_decoder import SlangDecoderAgent
from agents.weigher import WeigherAgent
from agents.compressor import CompressorAgent

# 加载环境变量
load_dotenv()


def print_separator(title: str = "", char: str = "="):
    """打印分隔线"""
    if title:
        print(f"\n{char * 80}")
        print(f"  {title}")
        print(f"{char * 80}")
    else:
        print(char * 80)


def test_comment_cleaner():
    """测试评论清洗智能体"""
    print_separator("测试 1: RawCommentCleaner - 评论清洗智能体")
    
    # 创建 LLM 提供者
    api_key = os.getenv("ARK_API_KEY")
    llm_provider = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60
    )
    
    # 创建智能体
    cleaner = RawCommentCleaner(llm_provider)
    
    # 测试数据
    test_comment = "这老板太坑了！就会画大饼，简直是学术妲己！经费是有的，但从不给学生发津贴。"
    
    print(f"\n原始评论:")
    print(f"  {test_comment}")
    
    # 处理
    result = cleaner.process(test_comment)
    
    print(f"\n处理结果:")
    print(f"  ✓ 事实内容: {result.factual_content}")
    print(f"  ✓ 情绪强度: {result.emotional_intensity:.2f}")
    print(f"  ✓ 关键词: {', '.join(result.keywords)}")
    print(f"  ✓ 处理时间: {result.execution_time:.2f}秒")
    
    return result


def test_slang_decoder():
    """测试黑话解码智能体"""
    print_separator("测试 2: SlangDecoderAgent - 黑话解码智能体")
    
    # 创建 LLM 提供者
    api_key = os.getenv("ARK_API_KEY")
    llm_provider = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60
    )
    
    # 创建智能体
    decoder = SlangDecoderAgent(
        llm_provider,
        storage_type="json",
        storage_path="./test_slang_dict.json"
    )
    
    # 测试数据
    test_text = "导师是'学术妲己'，就会画饼，还经常放羊不管学生。"
    
    print(f"\n待解码文本:")
    print(f"  {test_text}")
    
    # 处理
    result = decoder.process(test_text)
    
    print(f"\n处理结果:")
    print(f"  ✓ 解码后文本: {result.decoded_text}")
    print(f"\n  ✓ 识别的黑话:")
    for slang, meaning in result.slang_dictionary.items():
        print(f"    - '{slang}' → {meaning}")
    print(f"\n  ✓ 置信度: {result.confidence_score:.2f}")
    print(f"  ✓ 处理时间: {result.execution_time:.2f}秒")
    
    return result


def test_weigher():
    """测试权重分析智能体"""
    print_separator("测试 3: WeigherAgent - 权重分析智能体")
    
    # 创建 LLM 提供者
    api_key = os.getenv("ARK_API_KEY")
    llm_provider = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60
    )
    
    # 创建智能体
    weigher = WeigherAgent(llm_provider)
    
    # 测试数据
    from datetime import datetime
    test_input = {
        "content": "导师学术水平高，在领域内有影响力，但对学生要求严格",
        "source_metadata": {
            "platform": "知乎",
            "author_role": "博士生",
            "post_time": "2025-12-01"
        },
        "timestamp": datetime.now()
    }
    
    print(f"\n待分析内容:")
    print(f"  {test_input['content']}")
    print(f"\n来源信息:")
    print(f"  平台: {test_input['source_metadata']['platform']}")
    print(f"  作者角色: {test_input['source_metadata']['author_role']}")
    
    # 处理
    result = weigher.process(test_input)
    
    print(f"\n权重分析结果:")
    print(f"  ✓ 综合权重: {result.weight_score:.3f}")
    print(f"  ✓ 身份可信度: {result.identity_confidence:.3f}")
    print(f"  ✓ 时间衰减: {result.time_decay:.3f}")
    print(f"  ✓ 是否异常: {'是' if result.outlier_status else '否'}")
    print(f"\n  推理过程:")
    print(f"    {result.reasoning}")
    print(f"\n  ✓ 处理时间: {result.execution_time:.2f}秒")
    
    return result


def test_compressor():
    """测试结构化压缩智能体"""
    print_separator("测试 4: CompressorAgent - 结构化压缩智能体")
    
    # 创建 LLM 提供者
    api_key = os.getenv("ARK_API_KEY")
    llm_provider = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60
    )
    
    # 创建智能体
    compressor = CompressorAgent(llm_provider)
    
    # 测试数据
    test_input = {
        "factual_content": "导师学术水平高，在领域内有影响力，但对学生要求严格，学生压力大",
        "weight_score": 0.78,
        "keywords": ["学术水平", "影响力", "要求严格", "压力"],
        "original_nuance": "导师学术水平很高，在领域内很有影响力，但是对学生要求太严格了，压力山大。",
        "source_metadata": {
            "platform": "豆瓣",
            "author_role": "博士生"
        }
    }
    
    print(f"\n待压缩内容:")
    print(f"  事实: {test_input['factual_content']}")
    print(f"  权重: {test_input['weight_score']}")
    print(f"  关键词: {', '.join(test_input['keywords'])}")
    
    # 处理
    result = compressor.process(test_input)
    
    print(f"\n结构化知识节点:")
    node = result.structured_node
    print(f"  ✓ 导师ID: {node.mentor_id}")
    print(f"  ✓ 评价维度: {node.dimension}")
    print(f"  ✓ 事实内容: {node.fact_content}")
    print(f"  ✓ 综合权重: {node.weight_score:.3f}")
    print(f"  ✓ 标签: {', '.join(node.tags)}")
    print(f"\n  ✓ 压缩比: {result.compression_ratio:.2%}")
    print(f"  ✓ 处理时间: {result.execution_time:.2f}秒")
    
    return result


def main():
    print("\n" + "=" * 80)
    print("  del_agent 智能体功能测试 - 独立使用示例")
    print("=" * 80)
    print("\n本测试展示如何单独使用 del_agent 的各个智能体")
    print("每个智能体都可以独立使用，也可以组合使用")
    
    try:
        # 测试各个智能体
        test_comment_cleaner()
        test_slang_decoder()
        test_weigher()
        test_compressor()
        
        print_separator("所有测试完成", "=")
        print("\n✨ 测试总结:")
        print("  ✓ RawCommentCleaner: 去除情绪，提取事实")
        print("  ✓ SlangDecoderAgent: 识别和翻译学术黑话")
        print("  ✓ WeigherAgent: 评估信息可信度和权重")
        print("  ✓ CompressorAgent: 压缩为结构化知识节点")
        print("\n✨ 这些智能体可以:")
        print("  • 单独使用（如本测试）")
        print("  • 组合使用（通过 DataFactoryPipeline）")
        print("  • 配合核验循环（CriticAgent）提高质量")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
