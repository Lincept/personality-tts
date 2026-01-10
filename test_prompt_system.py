"""
测试语音助手 Prompt 系统
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.voice_assistant_prompt import VoiceAssistantPrompt

def test_basic_prompt():
    """测试基础 prompt 生成"""
    print("="*60)
    print("测试 1: 基础 Prompt")
    print("="*60)

    prompt_manager = VoiceAssistantPrompt()

    # 测试简单对话
    messages = prompt_manager.get_messages("你好")

    print("\n生成的消息列表:")
    for i, msg in enumerate(messages):
        print(f"\n消息 {i+1} ({msg['role']}):")
        print("-" * 40)
        print(msg['content'][:500] + "..." if len(msg['content']) > 500 else msg['content'])

    print("\n" + "="*60)

def test_with_user_info():
    """测试带用户信息的 prompt"""
    print("\n测试 2: 带用户信息的 Prompt")
    print("="*60)

    prompt_manager = VoiceAssistantPrompt()

    # 设置用户信息
    prompt_manager.set_user_info(
        name="小明",
        preferences={"运动": "攀岩", "饮食": "素食"},
        context={"位置": "北京", "天气": "晴天"}
    )

    messages = prompt_manager.get_messages("推荐一些适合我的活动")

    print("\n系统 Prompt (部分):")
    print("-" * 40)
    system_content = messages[0]['content']
    # 只显示用户信息部分
    if "## 用户信息" in system_content:
        start = system_content.index("## 用户信息")
        end = system_content.index("## 知识库") if "## 知识库" in system_content else len(system_content)
        print(system_content[start:end])

    print("\n" + "="*60)

def test_with_knowledge():
    """测试带知识库的 prompt"""
    print("\n测试 3: 带知识库的 Prompt")
    print("="*60)

    prompt_manager = VoiceAssistantPrompt()

    # 添加知识库
    prompt_manager.add_knowledge("用户最近在学习攀岩", category="兴趣")
    prompt_manager.add_knowledge("用户喜欢户外运动", category="兴趣")
    prompt_manager.add_knowledge("用户对素食感兴趣", category="饮食")

    messages = prompt_manager.get_messages("给我一些建议")

    print("\n系统 Prompt (知识库部分):")
    print("-" * 40)
    system_content = messages[0]['content']
    if "## 知识库" in system_content:
        start = system_content.index("## 知识库")
        print(system_content[start:start+300])

    print("\n" + "="*60)

def test_conversation_history():
    """测试对话历史管理"""
    print("\n测试 4: 对话历史管理")
    print("="*60)

    prompt_manager = VoiceAssistantPrompt()

    # 模拟多轮对话
    conversations = [
        ("你好", "你好！有什么可以帮你的吗？"),
        ("今天天气怎么样", "今天天气不错，阳光明媚，适合出门。"),
        ("推荐一些户外活动", "你可以去爬山、骑行或者野餐，都很不错。"),
    ]

    for user_msg, assistant_msg in conversations:
        prompt_manager.add_conversation("user", user_msg)
        prompt_manager.add_conversation("assistant", assistant_msg)

    # 获取新的消息
    messages = prompt_manager.get_messages("那我应该带什么装备？")

    print(f"\n对话历史条目数: {len(prompt_manager.conversation_history)}")
    print("\n最近的对话:")
    print("-" * 40)
    summary = prompt_manager.get_conversation_summary()
    print(summary)

    print("\n生成的消息列表长度:", len(messages))
    print("包含:")
    for msg in messages:
        print(f"  - {msg['role']}: {len(msg['content'])} 字符")

    print("\n" + "="*60)

def test_full_scenario():
    """测试完整场景"""
    print("\n测试 5: 完整场景模拟")
    print("="*60)

    prompt_manager = VoiceAssistantPrompt()

    # 设置用户信息
    prompt_manager.set_user_info(
        name="张三",
        preferences={"运动": "攀岩", "音乐": "摇滚"},
    )

    # 添加知识
    prompt_manager.add_knowledge("用户是攀岩初学者", category="运动")
    prompt_manager.add_knowledge("用户周末有空", category="时间")

    # 模拟对话
    prompt_manager.add_conversation("user", "你好")
    prompt_manager.add_conversation("assistant", "你好张三！有什么可以帮你的吗？")

    # 获取新消息
    messages = prompt_manager.get_messages("推荐一些攀岩装备")

    print("\n完整的系统 Prompt:")
    print("-" * 40)
    print(messages[0]['content'])

    print("\n\n对话历史:")
    print("-" * 40)
    for msg in messages[1:]:
        print(f"{msg['role']}: {msg['content']}")

    print("\n" + "="*60)

if __name__ == "__main__":
    test_basic_prompt()
    test_with_user_info()
    test_with_knowledge()
    test_conversation_history()
    test_full_scenario()

    print("\n✓ 所有测试完成！")
