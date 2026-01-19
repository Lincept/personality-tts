"""
测试火山引擎ARK API连接
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

api_key = os.getenv("ARK_API_KEY")
print(f"API Key: {api_key[:10]}...")

# 测试不同的base_url和model
# 根据火山引擎文档，尝试多个模型名称
test_configs = [
    {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-seed-1-6-251015"  # 示例中的模型
    },
    {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-pro-4k"
    },
    {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-lite-4k"
    },
    {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-pro-32k"
    },
    {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "ep-20250115192654-vdlhs"  # 之前的endpoint
    },
]

for config in test_configs:
    base_url = config["base_url"]
    model = config["model"]
    print(f"\n尝试连接: {base_url}")
    print(f"模型: {model}")
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=10,
            # 禁用代理
            http_client=None
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你好，请用一句话回答：什么是AI？"}
            ]
        )
        
        print(f"✓ 成功! 回答: {response.choices[0].message.content}")
        print(f"\n成功配置：")
        print(f"  base_url: {base_url}")
        print(f"  model: {model}")
        break
        
    except Exception as e:
        error_msg = str(e)
        print(f"✗ 失败: {error_msg[:300]}")
        if "404" in error_msg:
            print("   提示: Endpoint或模型不存在")
        elif "401" in error_msg:
            print("   提示: API密钥无效")
        elif "403" in error_msg:
            print("   提示: 无权限访问")

print("\n" + "="*80)
print("如果所有测试都失败，请参考 DOUBAO_CONFIG_GUIDE.md 获取帮助")
