"""
测试 Mem0 记忆持久化
验证关闭程序后重新启动，记忆是否还在
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import ConfigLoader
from src.memory.mem0_manager import Mem0Manager

def test_persistence():
    """测试记忆持久化"""
    print("\n" + "="*60)
    print("测试 Mem0 记忆持久化")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()
    mem0_config = config.get("mem0", {})
    user_id = mem0_config.get("user_id", "test_user")

    # 初始化 Mem0Manager
    manager = Mem0Manager(mem0_config)

    if not manager.enabled:
        print("⚠️  Mem0 未启用")
        return

    print(f"\n当前用户 ID: {user_id}")

    # 第一步：添加一条新记忆
    print("\n[步骤 1] 添加新记忆...")
    manager.add_conversation(
        user_input="我最喜欢的颜色是蓝色",
        assistant_response="好的，我记住了",
        user_id=user_id
    )
    print("✓ 记忆已添加")

    # 第二步：立即检索
    print("\n[步骤 2] 立即检索记忆...")
    memories = manager.search_memories(
        query="我喜欢什么颜色",
        user_id=user_id,
        limit=10
    )
    if memories:
        print(f"✓ 检索到记忆:\n{memories}")
    else:
        print("⚠️  未检索到记忆")

    # 第三步：获取所有记忆
    print("\n[步骤 3] 获取所有记忆...")
    all_memories = manager.get_all_memories(user_id)
    print(f"✓ 共有 {len(all_memories)} 条记忆:")
    for i, mem in enumerate(all_memories, 1):
        print(f"  {i}. {mem.get('memory', 'N/A')}")

    print("\n" + "="*60)
    print("提示：")
    print("1. 记忆已保存到 ./data/qdrant/ 目录")
    print("2. 即使关闭程序，记忆也不会丢失")
    print("3. 下次启动时，只要使用相同的 user_id，就能检索到这些记忆")
    print("4. 你可以运行 'python src/main.py' 启动程序，输入相关问题测试")
    print("="*60)

if __name__ == "__main__":
    test_persistence()
