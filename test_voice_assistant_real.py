"""
真实测试语音助手 Prompt 效果
使用实际的 LLM API 测试 prompt 是否能有效控制输出
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.voice_assistant_prompt import VoiceAssistantPrompt
from src.llm.llm_client import LLMClient
from src.config_loader import ConfigLoader

def test_with_real_llm():
    """使用真实 LLM 测试 prompt 效果"""
    print("="*60)
    print("真实 LLM 测试 - 验证 Prompt 控制效果")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    # 初始化 LLM
    llm_config = config.get("openai_compatible", {})
    llm_client = LLMClient(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        model=llm_config.get("model")
    )

    print(f"✓ LLM 初始化完成: {llm_client.get_model_info()}\n")

    # 初始化 Prompt 管理器
    prompt_manager = VoiceAssistantPrompt()

    # 设置用户信息
    prompt_manager.set_user_info(
        name="测试用户",
        preferences={"运动": "攀岩"}
    )

    # 测试用例
    test_cases = [
        {
            "name": "简单问候",
            "input": "你好",
            "expected": "简短、友好的问候"
        },
        {
            "name": "复杂问题（测试是否会输出列表）",
            "input": "推荐一些攀岩装备",
            "expected": "简短回答，不使用列表格式"
        },
        {
            "name": "技术问题（测试是否会输出长篇）",
            "input": "介绍一下 Python 编程语言",
            "expected": "简短介绍，不超过 50 字"
        },
        {
            "name": "开放性问题",
            "input": "今天天气怎么样",
            "expected": "简短回答，带互动"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"{'='*60}")
        print(f"用户输入: {test_case['input']}")
        print(f"期望: {test_case['expected']}")
        print(f"\n助手回复:")
        print("-" * 60)

        # 获取消息
        messages = prompt_manager.get_messages(test_case['input'])

        # 调用 LLM（流式输出）
        full_response = ""
        for chunk in llm_client.chat_stream(messages=messages, temperature=0.7):
            print(chunk, end="", flush=True)
            full_response += chunk

        print("\n" + "-" * 60)

        # 分析输出
        print(f"\n分析:")
        print(f"  - 字数: {len(full_response)}")
        print(f"  - 是否包含 Markdown: {'是' if any(md in full_response for md in ['**', '###', '```', '- ', '* ']) else '否'}")
        print(f"  - 是否包含列表: {'是' if any(lst in full_response for lst in ['1.', '2.', '3.', '- ', '* ']) else '否'}")
        print(f"  - 是否简洁: {'是' if len(full_response) <= 60 else '否（超过 60 字）'}")

        # 保存对话历史
        prompt_manager.add_conversation("user", test_case['input'])
        prompt_manager.add_conversation("assistant", full_response)

        input("\n按回车继续下一个测试...")

    print("\n" + "="*60)
    print("✓ 所有测试完成！")
    print("="*60)

def test_different_roles():
    """测试不同角色的效果"""
    print("\n" + "="*60)
    print("测试不同角色")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    # 初始化 LLM
    llm_config = config.get("openai_compatible", {})
    llm_client = LLMClient(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        model=llm_config.get("model")
    )

    roles = ["default", "casual", "professional", "companion"]
    test_input = "今天心情不太好"

    for role in roles:
        print(f"\n{'='*60}")
        print(f"角色: {role}")
        print(f"{'='*60}")

        prompt_manager = VoiceAssistantPrompt(role=role)
        role_info = prompt_manager.get_role_info()

        print(f"角色信息:")
        print(f"  - 名称: {role_info['name']}")
        print(f"  - 风格: {role_info['style']}")
        print(f"  - 特点: {role_info['personality']}")

        print(f"\n用户: {test_input}")
        print(f"助手回复:")
        print("-" * 60)

        messages = prompt_manager.get_messages(test_input)

        full_response = ""
        for chunk in llm_client.chat_stream(messages=messages, temperature=0.7):
            print(chunk, end="", flush=True)
            full_response += chunk

        print("\n" + "-" * 60)
        print(f"字数: {len(full_response)}")

        input("\n按回车继续下一个角色...")

    print("\n✓ 角色测试完成！")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试语音助手 Prompt")
    parser.add_argument("--test", choices=["basic", "roles", "all"], default="basic",
                       help="测试类型: basic(基础测试), roles(角色测试), all(全部)")

    args = parser.parse_args()

    if args.test == "basic":
        test_with_real_llm()
    elif args.test == "roles":
        test_different_roles()
    elif args.test == "all":
        test_with_real_llm()
        test_different_roles()
