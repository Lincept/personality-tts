"""
测试两阶段记忆增强对话

测试场景：
1. 用户自我介绍 → 应该触发存储
2. 询问记忆 → 应该触发检索
3. 普通闲聊 → 不应该触发检索/存储
"""

import os
import sys
import logging

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)

from config_loader import ConfigLoader
from memory.memory_chat import MemoryEnhancedChat, create_memory_chat
from memory.mem0_manager import Mem0Manager

# 配置日志输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/memory_chat.log", encoding="utf-8")
    ]
)


def test_basic_flow():
    """测试基本流程"""
    print("\n" + "="*60)
    print("测试：两阶段记忆增强对话")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    # 创建 Mem0 管理器
    mem0_config = config.get("mem0", {})
    mem0_manager = None
    if mem0_config.get("enable_mem0", False):
        mem0_manager = Mem0Manager(mem0_config)
        print("✓ Mem0 初始化成功")

    # 获取 LLM 配置
    llm_config = config.get("openai_compatible", {})

    # 创建 MemoryEnhancedChat
    chat = MemoryEnhancedChat(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        model=llm_config.get("model", "qwen3-max"),
        mem0_manager=mem0_manager,
        user_id="test_user",
        role_description="你是一个友好的语音助手，说话简洁自然",
        verbose=True  # 开启详细日志
    )

    print(f"✓ MemoryEnhancedChat 初始化成功")
    print(f"  模型: {chat.model}")
    print()

    # 对话历史
    history = []

    # ========== 测试 1: 自我介绍（应触发存储）==========
    print("-"*40)
    print("测试 1: 用户自我介绍")
    print("-"*40)

    user_input = "我叫张三，我是一名软件工程师"
    print(f"用户: {user_input}")

    response = chat.chat(user_input, history)
    print(f"助手: {response}")

    # 更新历史
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})
    print()

    # ========== 测试 2: 询问名字（应触发检索）==========
    print("-"*40)
    print("测试 2: 询问用户名字")
    print("-"*40)

    user_input = "你还记得我叫什么吗？"
    print(f"用户: {user_input}")

    response = chat.chat(user_input, history)
    print(f"助手: {response}")

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})
    print()

    # ========== 测试 3: 普通闲聊（不应触发检索/存储）==========
    print("-"*40)
    print("测试 3: 普通闲聊")
    print("-"*40)

    user_input = "今天天气怎么样？"
    print(f"用户: {user_input}")

    response = chat.chat(user_input, history)
    print(f"助手: {response}")

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})
    print()

    # ========== 测试 4: 分享偏好（应触发存储）==========
    print("-"*40)
    print("测试 4: 分享偏好")
    print("-"*40)

    user_input = "我喜欢打篮球和游泳"
    print(f"用户: {user_input}")

    response = chat.chat(user_input, history)
    print(f"助手: {response}")

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})
    print()

    # ========== 测试 5: 询问偏好（应触发检索）==========
    print("-"*40)
    print("测试 5: 询问偏好")
    print("-"*40)

    user_input = "你知道我喜欢什么运动吗？"
    print(f"用户: {user_input}")

    response = chat.chat(user_input, history)
    print(f"助手: {response}")
    print()

    # ========== 测试 6: 分享关系（应触发存储，type=relationship）==========
    print("-"*40)
    print("测试 6: 分享人际关系")
    print("-"*40)

    user_input = "小明是我的好朋友，我们经常一起打球"
    print(f"用户: {user_input}")

    response = chat.chat(user_input, history)
    print(f"助手: {response}")
    print()

    print("="*60)
    print("测试完成！")
    print("="*60)


def test_stream_flow():
    """测试流式输出"""
    print("\n" + "="*60)
    print("测试：流式输出")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    # 创建 Mem0 管理器
    mem0_config = config.get("mem0", {})
    mem0_manager = None
    if mem0_config.get("enable_mem0", False):
        mem0_manager = Mem0Manager(mem0_config)

    # 获取 LLM 配置
    llm_config = config.get("openai_compatible", {})

    # 创建 MemoryEnhancedChat
    chat = MemoryEnhancedChat(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        model=llm_config.get("model", "qwen3-max"),
        mem0_manager=mem0_manager,
        user_id="test_user",
        role_description="你是一个友好的语音助手",
        verbose=True
    )

    print("测试流式输出...")
    print("-"*40)

    user_input = "给我讲一个简短的笑话"
    print(f"用户: {user_input}")
    print(f"助手: ", end="", flush=True)

    for chunk in chat.chat_stream(user_input, []):
        print(chunk, end="", flush=True)

    print("\n")
    print("="*60)


def test_create_helper():
    """测试便捷创建函数"""
    print("\n" + "="*60)
    print("测试：便捷创建函数")
    print("="*60)

    config_loader = ConfigLoader()
    config = config_loader.get_config()

    chat = create_memory_chat(
        config=config,
        role_description="你是一个友好的助手",
        verbose=True
    )

    print(f"✓ 通过 create_memory_chat 创建成功")
    print(f"  模型: {chat.model}")
    print(f"  用户ID: {chat.user_id}")

    response = chat.chat("你好！", [])
    print(f"  测试回复: {response}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试两阶段记忆增强对话")
    parser.add_argument("--test", choices=["basic", "stream", "helper", "all"],
                        default="basic", help="选择测试类型")

    args = parser.parse_args()

    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)

    if args.test == "basic" or args.test == "all":
        test_basic_flow()

    if args.test == "stream" or args.test == "all":
        test_stream_flow()

    if args.test == "helper" or args.test == "all":
        test_create_helper()
