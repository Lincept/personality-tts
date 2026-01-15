#!/usr/bin/env python3
"""
文字对话模式 - 你打字，AI 说话
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import LLMTTSTest
from src.role_loader import RoleLoader


def main():
    """文字对话模式主函数"""
    print('\n' + '='*60)
    print('💬 文字对话模式')
    print('='*60)
    print('\n✨ 支持智能记忆功能')
    print('   - LLM 会自动保存重要信息')
    print('   - 使用 /memories 查看记忆')
    print('   - 使用 /help 查看所有命令\n')

    # 加载默认角色
    role_loader = RoleLoader()
    role_config = role_loader.get_role("natural")  # 使用自然助手角色

    print(f"正在初始化...")

    # 初始化
    test = LLMTTSTest(role_config=role_config)
    test.initialize_llm()

    print("✓ 初始化完成\n")

    # 进入交互模式（使用实时模式）
    test.interactive_mode(use_realtime=True)


if __name__ == '__main__':
    main()
