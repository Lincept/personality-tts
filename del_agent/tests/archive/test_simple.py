"""
简单的豆包模型测试 - 只测试基础功能
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from core.llm_adapter import OpenAICompatibleProvider
from agents.raw_comment_cleaner import RawCommentCleaner

# 加载环境变量
load_dotenv()

print("=" * 80)
print("豆包模型快速测试")
print("=" * 80)

# 获取API Key
api_key = os.getenv("ARK_API_KEY")
print(f"\n✓ API Key: {api_key[:10]}...")

# 创建LLM提供者
print("\n创建LLM提供者...")
llm_provider = OpenAICompatibleProvider(
    model_name="doubao-seed-1-6-251015",
    api_key=api_key,
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    timeout=60
)
print("✓ LLM提供者创建成功")

# 测试1: 简单对话
print("\n" + "-" * 80)
print("测试1: 基础对话")
print("-" * 80)
try:
    messages = [
        {"role": "user", "content": "请用一句话介绍人工智能"}
    ]
    response = llm_provider.generate(messages)
    print(f"✓ 成功!")
    print(f"回答: {response}")
except Exception as e:
    print(f"✗ 失败: {str(e)[:200]}")

# 测试2: 评论清洗
print("\n" + "-" * 80)
print("测试2: 评论清洗智能体")
print("-" * 80)
try:
    cleaner = RawCommentCleaner(llm_provider)
    print("✓ 智能体初始化成功")
    
    test_comment = "这老板简直是'学术妲己'，太会画饼了！经费倒是多，但不发给我们。"
    print(f"\n原始评论: {test_comment}")
    
    result = cleaner.process(test_comment)
    print(f"\n✓ 清洗成功!")
    print(f"事实内容: {result.factual_content}")
    print(f"情绪强度: {result.sentiment_intensity}")
    
except Exception as e:
    print(f"\n✗ 失败: {str(e)[:300]}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
