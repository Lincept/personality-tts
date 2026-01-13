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
    print('💬 文字对话模式 - 你打字，AI 说话')
    print('='*60)
    print('\n提示:')
    print('  - 输入文字，AI 会朗读回复')
    print('  - 输入 /quit 退出')
    print('  - 输入 /help 查看更多命令\n')

    # 加载默认角色
    role_loader = RoleLoader()
    role_config = role_loader.get_role("default")

    # 初始化
    test = LLMTTSTest(role_config=role_config)
    test.initialize_llm()

    # 进入交互模式（使用实时模式）
    test.interactive_mode(use_realtime=True)


if __name__ == '__main__':
    main()
