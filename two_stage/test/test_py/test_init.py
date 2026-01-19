#!/usr/bin/env python3
"""
快速初始化测试 - 验证 LLMTTSTest 类能否正常初始化
"""
import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from src.main import LLMTTSTest
from src.role_loader import RoleLoader


def test_initialization():
    """测试初始化"""
    print("\n" + "="*60)
    print("LLMTTSTest 初始化测试")
    print("="*60)
    
    try:
        # 加载角色
        print("\n1. 加载角色配置...")
        role_loader = RoleLoader()
        role_config = role_loader.get_role("natural")
        print(f"   ✅ 角色加载成功: {role_config['name']}")
        
        # 初始化 LLMTTSTest
        print("\n2. 初始化 LLMTTSTest...")
        test = LLMTTSTest(role_config=role_config)
        print("   ✅ LLMTTSTest 初始化成功")
        
        # 检查配置
        print("\n3. 检查配置...")
        print(f"   输出目录: {test.output_dir}")
        print(f"   记忆管理器: {'已启用' if test.mem0_manager else '未启用'}")
        print(f"   角色描述: {test.role_description}")
        print("   ✅ 配置检查通过")
        
        # 初始化 LLM（需要 API Key）
        print("\n4. 初始化 LLM 客户端...")
        try:
            test.initialize_llm()
            print("   ✅ LLM 客户端初始化成功")
        except Exception as e:
            print(f"   ⚠️ LLM 初始化失败（可能未配置 API Key）: {e}")
        
        print("\n" + "="*60)
        print("✅ 初始化测试完成")
        print("="*60)
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ 文件未找到: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(test_initialization())
