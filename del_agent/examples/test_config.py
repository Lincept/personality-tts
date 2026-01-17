#!/usr/bin/env python
"""
测试 .env 配置是否正确加载
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from del_agent.utils.config import get_config_manager

def main():
    print("=== Del Agent 配置测试 ===\n")
    
    # 获取配置管理器
    config_manager = get_config_manager()
    
    # 检查环境变量
    print("1. 环境变量检查:")
    env_vars = {
        'DOBAO_API_KEY': os.getenv('DOBAO_API_KEY'),
        'DOBAO_API_SECRET': os.getenv('DOBAO_API_SECRET'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY'),
        'MOONSHOT_API_KEY': os.getenv('MOONSHOT_API_KEY'),
        'QWEN_API_KEY': os.getenv('QWEN_API_KEY'),
    }
    
    for key, value in env_vars.items():
        if value:
            masked_value = value[:10] + '...' if len(value) > 10 else value
            print(f"   ✓ {key}: {masked_value}")
        else:
            print(f"   ✗ {key}: 未设置")
    
    # 检查 LLM 配置
    print("\n2. LLM 提供者配置:")
    for provider_name in config_manager.list_llm_configs():
        llm_config = config_manager.get_llm_config(provider_name)
        api_key_status = "已设置" if llm_config.api_key else "未设置"
        print(f"   - {provider_name}: {llm_config.model_name} (API Key: {api_key_status})")
    
    # 检查智能体配置
    print("\n3. 智能体配置:")
    for agent_name in config_manager.list_agent_configs():
        agent_config = config_manager.get_agent_config(agent_name)
        print(f"   - {agent_name}: 使用 {agent_config.llm_config.provider}")
    
    # 获取默认智能体
    default_agent = config_manager.get_agent_config('comment_cleaner')
    print(f"\n4. 默认智能体: {default_agent.name}")
    print(f"   LLM 提供者: {default_agent.llm_config.provider}")
    print(f"   模型: {default_agent.llm_config.model_name}")
    print(f"   API Key 状态: {'已配置' if default_agent.llm_config.api_key else '未配置'}")
    
    # 提示
    print("\n=== 测试完成 ===")
    if not default_agent.llm_config.api_key:
        print("\n⚠️  提示: 默认使用的 LLM 提供者的 API Key 未配置")
        print(f"   请在 .env 文件中设置 {default_agent.llm_config.provider.upper()}_API_KEY")
    else:
        print("\n✓ 配置正常，可以运行 demo.py")

if __name__ == "__main__":
    main()
