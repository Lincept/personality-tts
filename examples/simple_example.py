"""
简单示例 - 快速开始
"""
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import LLMTTSTest


def example_basic():
    """基础示例: 单次对话"""
    print("=== 示例1: 基础对话 ===\n")

    test = LLMTTSTest()
    test.chat_and_speak(
        prompt="你好,请用一句话介绍一下你自己",
        tts_provider="qwen3",
        play_audio=True,
        stream=True
    )


def example_compare():
    """示例2: 对比不同TTS提供商"""
    print("\n=== 示例2: 对比TTS提供商 ===\n")

    test = LLMTTSTest()
    test.compare_tts_providers(
        prompt="今天天气真不错,适合出去散步",
        play_audio=True
    )


def example_multiple_questions():
    """示例3: 多轮对话"""
    print("\n=== 示例3: 多轮对话 ===\n")

    test = LLMTTSTest()

    questions = [
        "什么是人工智能?",
        "请推荐一本好书",
        "如何保持健康?"
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n--- 第 {i} 轮对话 ---")
        test.chat_and_speak(
            prompt=question,
            tts_provider="qwen3",
            play_audio=True,
            stream=True
        )
        print()


def example_different_providers():
    """示例4: 测试不同TTS提供商"""
    print("\n=== 示例4: 测试不同TTS提供商 ===\n")

    test = LLMTTSTest()
    prompt = "欢迎使用语音助手"

    providers = ["qwen3", "volcengine", "minimax"]

    for provider in providers:
        print(f"\n--- 测试 {provider} ---")
        test.chat_and_speak(
            prompt=prompt,
            tts_provider=provider,
            play_audio=True,
            stream=False
        )


if __name__ == "__main__":
    # 运行示例
    print("选择示例:")
    print("1. 基础对话")
    print("2. 对比TTS提供商")
    print("3. 多轮对话")
    print("4. 测试不同TTS提供商")

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice == "1":
        example_basic()
    elif choice == "2":
        example_compare()
    elif choice == "3":
        example_multiple_questions()
    elif choice == "4":
        example_different_providers()
    else:
        print("无效选项")
