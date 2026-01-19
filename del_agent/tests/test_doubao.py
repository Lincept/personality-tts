"""
AI Data Factory - 豆包模型真实测试
使用火山引擎ARK API测试完整的数据工厂流水线
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from core.llm_adapter import OpenAICompatibleProvider
from backend.factory import DataFactoryPipeline
from models.schemas import RawReview

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")


def load_ark_api():
    """加载火山引擎ARK API配置"""
    load_dotenv()
    
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        raise ValueError("ARK_API_KEY not found in .env file")
    
    logger.info(f"✓ ARK API Key loaded: {api_key[:8]}...")
    return api_key


def create_test_reviews():
    """创建测试评论数据"""
    return [
        RawReview(
            review_id="test_001",
            content="这老板简直是'学术妲己'，太会画饼了！经费倒是多，但不发给我们。实验室设备老旧，申请新设备总是拖延。",
            source="test",
            timestamp=datetime.now()
        ),
        RawReview(
            review_id="test_002",
            content="实验室氛围还行，师兄师姐都挺友好的，导师人也不错。就是项目方向有点冷门，担心毕业后不好找工作。",
            source="test",
            timestamp=datetime.now()
        ),
        RawReview(
            review_id="test_003",
            content="导师是'学阀'，天天让我们给他干私活，还不给钱。论文署名也不公平，明明是我做的工作，他要挂第一作者。压榨学生太严重了！",
            source="test",
            timestamp=datetime.now()
        ),
        RawReview(
            review_id="test_004",
            content="研究方向挺前沿的，实验室也有充足的经费支持。导师指导很认真，定期开组会讨论进展。就是发论文压力比较大。",
            source="test",
            timestamp=datetime.now()
        ),
        RawReview(
            review_id="test_005",
            content="这个组简直是'血汗工厂'！每天工作12小时以上，周末也不让休息。老板还喜欢PUA，动不动就说我们不努力。受不了了！",
            source="test",
            timestamp=datetime.now()
        ),
    ]


def test_basic_llm():
    """测试1：基础LLM连接"""
    print_separator("测试1：基础LLM连接测试")
    
    try:
        api_key = load_ark_api()
        
        # 创建LLM提供者（使用火山引擎ARK API）
        llm_provider = OpenAICompatibleProvider(
            model_name="doubao-seed-1-6-251015",  # 豆包模型
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            timeout=60
        )
        
        # 测试简单对话
        messages = [
            {"role": "system", "content": "你是一个有帮助的AI助手。"},
            {"role": "user", "content": "请用一句话介绍什么是AI。"}
        ]
        
        logger.info("发送测试消息...")
        response = llm_provider.generate(messages, temperature=0.7)
        
        print("✓ LLM连接成功！")
        print(f"回答: {response}")
        print_separator()
        return True
        
    except Exception as e:
        logger.error(f"✗ LLM连接失败: {str(e)}", exc_info=True)
        return False


def test_comment_cleaner():
    """测试2：评论清洗智能体"""
    print_separator("测试2：评论清洗智能体测试")
    
    try:
        api_key = load_ark_api()
        
        # 创建LLM提供者
        llm_provider = OpenAICompatibleProvider(
            model_name="doubao-seed-1-6-251015",
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            timeout=60
        )
        
        # 创建数据工厂流水线（不启用验证）
        pipeline = DataFactoryPipeline(
            llm_provider=llm_provider,
            enable_verification=False
        )
        
        # 创建测试评论
        test_reviews = create_test_reviews()
        
        # 处理第一条评论
        review = test_reviews[0]
        print(f"原始评论: {review.content}\n")
        
        logger.info("开始清洗评论...")
        result = pipeline.cleaner.process(review.content)
        
        print("✓ 评论清洗成功！")
        print(f"\n清洗结果:")
        print(f"  - 事实内容: {result.factual_content}")
        print(f"  - 情绪强度: {result.emotional_intensity}")
        print(f"  - 原始评论长度: {len(review.content)} 字符")
        print(f"  - 清洗后长度: {len(result.factual_content)} 字符")
        print_separator()
        return True
        
    except Exception as e:
        logger.error(f"✗ 评论清洗失败: {str(e)}", exc_info=True)
        return False


def test_full_pipeline():
    """测试3：完整流水线"""
    print_separator("测试3：完整数据工厂流水线测试")
    
    try:
        api_key = load_ark_api()
        
        # 创建LLM提供者
        llm_provider = OpenAICompatibleProvider(
            model_name="doubao-seed-1-6-251015",
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            timeout=60
        )
        
        # 创建数据工厂流水线（不启用验证）
        del_agent_root = Path(__file__).resolve().parents[1]
        slang_dict_path = del_agent_root / "data" / "slang_dict.json"

        pipeline = DataFactoryPipeline(
            llm_provider=llm_provider,
            enable_verification=False,
            slang_dict_storage="json",
            slang_dict_path=str(slang_dict_path)
        )
        
        # 创建测试评论
        test_reviews = create_test_reviews()
        
        # 处理所有评论
        results = []
        for i, review in enumerate(test_reviews, 1):
            print(f"\n处理评论 {i}/{len(test_reviews)}...")
            print(f"原始内容: {review.content[:50]}...")
            
            try:
                result = pipeline.process_raw_review(review)
                results.append(result)
                
                print(f"✓ 处理成功")
                print(f"  - 导师ID: {result.mentor_id}")
                print(f"  - 维度: {result.dimension}")
                print(f"  - 权重评分: {result.weight_score:.2f}")
                
            except Exception as e:
                logger.error(f"✗ 处理失败: {str(e)}")
                continue
        
        # 打印统计信息
        print_separator()
        print(f"流水线统计:")
        print(f"  - 总评论数: {len(test_reviews)}")
        print(f"  - 成功处理: {len(results)}")
        print(f"  - 失败数量: {len(test_reviews) - len(results)}")
        print(f"  - 成功率: {len(results)/len(test_reviews)*100:.1f}%")
        
        # 显示黑话词典
        print(f"\n黑话词典:")
        slang_dict = pipeline.decoder.dictionary_store.get_all()
        for slang, definition in slang_dict.items():
            print(f"  - '{slang}': {definition}")
        
        # 保存结果
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                [result.model_dump() for result in results],
                f,
                ensure_ascii=False,
                indent=2,
                default=str
            )
        
        print(f"\n✓ 结果已保存到: {output_file}")
        print_separator()
        return True
        
    except Exception as e:
        logger.error(f"✗ 流水线测试失败: {str(e)}", exc_info=True)
        return False


def main():
    """主函数"""
    print_separator("AI Data Factory - 豆包模型真实测试")
    print("使用火山引擎ARK API")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator()
    
    # 运行测试
    tests = [
        ("基础LLM连接", test_basic_llm),
        ("评论清洗智能体", test_comment_cleaner),
        ("完整流水线", test_full_pipeline),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"测试 '{test_name}' 发生异常: {str(e)}")
            results[test_name] = False
    
    # 打印测试总结
    print_separator("测试总结")
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print_separator()
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请查看日志。")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
