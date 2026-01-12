"""
直接测试 Mem0 的添加和检索功能
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import ConfigLoader
from src.memory.mem0_manager import Mem0Manager

def test_mem0_directly():
    """直接测试 Mem0"""
    print("\n" + "="*60)
    print("直接测试 Mem0 功能")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()
    mem0_config = config.get("mem0", {})
    user_id = "test_user"

    # 初始化 Mem0Manager
    manager = Mem0Manager(mem0_config)

    if not manager.enabled:
        print("⚠️  Mem0 未启用")
        return

    print(f"\n当前用户 ID: {user_id}")

    # 步骤 1：添加记忆
    print("\n[步骤 1] 添加记忆...")
    try:
        manager.add_conversation(
            user_input="我叫王五，是一名设计师",
            assistant_response="你好王五！",
            user_id=user_id
        )
        print("✓ 记忆添加成功")
    except Exception as e:
        print(f"❌ 记忆添加失败: {e}")
        import traceback
        traceback.print_exc()

    # 等待处理
    import time
    print("\n等待 3 秒让 Mem0 处理...")
    time.sleep(3)

    # 步骤 2：使用 Mem0 原生 API 获取记忆
    print("\n[步骤 2] 使用 Mem0 原生 API 获取记忆...")
    try:
        result = manager.memory.get_all(user_id=user_id)
        print(f"原生 API 返回: {result}")

        if result and "results" in result:
            memories = result["results"]
            print(f"✓ 找到 {len(memories)} 条记忆:")
            for i, mem in enumerate(memories, 1):
                print(f"  {i}. {mem}")
        else:
            print("⚠️  未找到记忆")
    except Exception as e:
        print(f"❌ 获取记忆失败: {e}")
        import traceback
        traceback.print_exc()

    # 步骤 3：测试检索
    print("\n[步骤 3] 测试记忆检索...")
    try:
        results = manager.search_memories(
            query="我的名字",
            user_id=user_id,
            limit=5
        )
        if results:
            print(f"✓ 检索到记忆:\n{results}")
        else:
            print("⚠️  未检索到记忆")
    except Exception as e:
        print(f"❌ 检索失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == "__main__":
    test_mem0_directly()
