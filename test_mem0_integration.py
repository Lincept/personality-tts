"""
Mem0 整合测试脚本
测试 Mem0 是否正确集成到 personality-tts 项目中
"""
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import ConfigLoader
from src.memory.mem0_manager import Mem0Manager

def test_config_loading():
    """测试配置加载"""
    print("\n" + "="*60)
    print("测试 1: 配置加载")
    print("="*60)

    config_loader = ConfigLoader()
    config = config_loader.get_config()

    mem0_config = config.get("mem0", {})
    print(f"✓ Mem0 配置加载成功")
    print(f"  - 启用状态: {mem0_config.get('enable_mem0', False)}")
    print(f"  - LLM 模型: {mem0_config.get('llm_model', 'N/A')}")
    print(f"  - 用户 ID: {mem0_config.get('user_id', 'N/A')}")

    return mem0_config

def test_mem0_manager_init(mem0_config):
    """测试 Mem0Manager 初始化"""
    print("\n" + "="*60)
    print("测试 2: Mem0Manager 初始化")
    print("="*60)

    try:
        manager = Mem0Manager(mem0_config)
        if manager.enabled:
            print("✓ Mem0Manager 初始化成功")
            return manager
        else:
            print("⚠️  Mem0Manager 未启用")
            return None
    except Exception as e:
        print(f"❌ Mem0Manager 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_memory_operations(manager, user_id):
    """测试记忆操作"""
    print("\n" + "="*60)
    print("测试 3: 记忆操作")
    print("="*60)

    if not manager or not manager.enabled:
        print("⚠️  跳过测试（Mem0 未启用）")
        return

    try:
        # 测试添加记忆
        print("\n[3.1] 添加对话记忆...")
        manager.add_conversation(
            user_input="我叫张三，是一名程序员",
            assistant_response="你好张三！很高兴认识你",
            user_id=user_id
        )
        print("✓ 对话记忆添加成功")

        # 测试检索记忆
        print("\n[3.2] 检索记忆...")
        memories = manager.search_memories(
            query="我的名字",
            user_id=user_id,
            limit=5
        )
        if memories:
            print(f"✓ 检索到记忆:\n{memories}")
        else:
            print("⚠️  未检索到记忆（可能需要等待索引）")

        # 测试获取所有记忆
        print("\n[3.3] 获取所有记忆...")
        all_memories = manager.get_all_memories(user_id)
        print(f"✓ 共有 {len(all_memories)} 条记忆")
        for i, mem in enumerate(all_memories, 1):
            print(f"  {i}. {mem.get('memory', 'N/A')}")

        # 测试清除记忆
        print("\n[3.4] 清除记忆...")
        manager.clear_memories(user_id)

        remaining = manager.get_all_memories(user_id)
        if len(remaining) == 0:
            print("✓ 记忆清除成功")
        else:
            print(f"⚠️  还有 {len(remaining)} 条记忆未清除")

    except Exception as e:
        print(f"❌ 记忆操作失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Mem0 整合测试")
    print("="*60)

    # 测试 1: 配置加载
    mem0_config = test_config_loading()

    # 测试 2: Mem0Manager 初始化
    manager = test_mem0_manager_init(mem0_config)

    # 测试 3: 记忆操作
    user_id = mem0_config.get('user_id', 'test_user')
    test_memory_operations(manager, user_id)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
