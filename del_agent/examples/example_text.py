#!/usr/bin/env python3
"""
DEL Agent 文本交互示例
演示如何使用 DEL Agent 进行文本对话交互

版本：1.0.0
创建：2026-01-19
"""

import sys
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from del_agent.frontend.orchestrator import FrontendOrchestrator
from del_agent.core.llm_adapter import OpenAICompatibleProvider


async def main():
    """
    文本交互示例主函数
    
    演示功能：
    1. 创建 FrontendOrchestrator
    2. 处理用户输入
    3. 显示助手回复
    4. 多轮对话
    """
    
    print("=" * 60)
    print("DEL Agent 文本交互示例")
    print("=" * 60)
    print()
    
    # ====================================
    # Step 1: 创建 LLM Provider
    # ====================================
    print("📝 Step 1: 初始化 LLM Provider...")
    
    # 加载环境变量 - 从del_agent目录加载
    env_path = PROJECT_ROOT / "del_agent" / ".env"
    load_dotenv(dotenv_path=env_path)
    
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        print(f"   ✗ 错误: 未找到 ARK_API_KEY 环境变量")
        print(f"   请在 {env_path} 文件中配置 ARK_API_KEY")
        return
    
    # 创建豆包 LLM Provider
    llm_provider = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",  # 豆包模型
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60,
        reasoning_effort="minimal"  # 不启用思考模式，提高响应速度
    )
    
    print("   ✓ LLM Provider 初始化成功 (使用豆包API)")
    print()
    
    # ====================================
    # Step 2: 创建 FrontendOrchestrator
    # ====================================
    print("📝 Step 2: 创建 FrontendOrchestrator...")
    
    orchestrator = FrontendOrchestrator(
        llm_provider=llm_provider,
        enable_rag=False  # 暂时不启用 RAG
    )
    
    print("   ✓ Orchestrator 创建成功")
    print()
    
    # ====================================
    # Step 3: 单次对话示例
    # ====================================
    print("📝 Step 3: 单次对话示例")
    print("-" * 60)
    
    user_id = "demo_user"
    user_input = "你好，今天天气不错"
    
    print(f"用户: {user_input}")
    
    result = await orchestrator.process_user_input(
        user_id=user_id,
        user_input=user_input
    )
    
    if result["success"]:
        response_text = result.get('response_text', '(无响应)')
        if not response_text or response_text.strip() == '':
            print(f"助手: (响应为空，可能是LLM返回异常)")
            print(f"[调试] 完整结果: {result}")
        else:
            print(f"助手: {response_text}")
        print(f"\n[调试] 意图: {result['intent_type']}, "
              f"执行时间: {result['execution_time']:.2f}s")
    else:
        print(f"[错误] {result.get('error_message', '处理失败')}")
    
    print()
    
    # ====================================
    # Step 4: 多轮对话示例
    # ====================================
    print("📝 Step 4: 多轮对话示例")
    print("-" * 60)
    
    conversation = [
        "我想找一家好吃的川菜馆",
        "有什么推荐吗？",
        "谢谢你的建议！"
    ]
    
    for i, user_msg in enumerate(conversation, 1):
        print(f"\n第 {i} 轮对话:")
        print(f"用户: {user_msg}")
        
        result = await orchestrator.process_user_input(
            user_id=user_id,
            user_input=user_msg
        )
        
        if result["success"]:
            response_text = result.get('response_text', '(无响应)')
            if not response_text or response_text.strip() == '':
                print(f"助手: (响应为空)")
            else:
                print(f"助手: {response_text}")
        else:
            print(f"[错误] {result.get('error_message', '处理失败')}")
    
    print()
    
    # ====================================
    # Step 5: 查看对话历史
    # ====================================
    print("📝 Step 5: 查看对话历史")
    print("-" * 60)
    
    stats = orchestrator.get_conversation_stats(user_id)
    if stats:
        print(f"对话轮数: {stats['conversation_turns']}")
        print(f"创建时间: {stats['created_at']}")
        print(f"最后交互: {stats['last_interaction']}")
        print(f"总交互次数: {stats['total_interactions']}")
    else:
        print("暂无对话历史")
    
    print()
    
    # ====================================
    # Step 6: 用户画像
    # ====================================
    print("📝 Step 6: 查看用户画像")
    print("-" * 60)
    
    profile = orchestrator.profile_manager.get_profile(user_id)
    if profile:
        print(f"交互次数: {profile.interaction_history_count}")
        print(f"幽默偏好: {profile.humor_preference:.2f}")
        print(f"正式度: {profile.formality_level:.2f}")
        print(f"细节偏好: {profile.detail_preference:.2f}")
        print(f"语言风格: {profile.language_style}")
        if profile.preferred_topics:
            print(f"关注话题: {', '.join(profile.preferred_topics)}")
    else:
        print("暂无用户画像")
    
    print()
    
    # ====================================
    # Step 7: 清空对话
    # ====================================
    print("📝 Step 7: 清空对话历史")
    print("-" * 60)
    
    orchestrator.clear_conversation(user_id)
    print("✓ 对话历史已清空")
    
    print()
    print("=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
