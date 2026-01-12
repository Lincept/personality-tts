"""
检查所有用户的记忆
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import ConfigLoader
from src.memory.mem0_manager import Mem0Manager

def check_all_users():
    """检查所有用户的记忆"""
    print("\n" + "="*60)
    print("检查所有用户的记忆")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()
    mem0_config = config.get("mem0", {})

    # 初始化 Mem0Manager
    manager = Mem0Manager(mem0_config)

    if not manager.enabled:
        print("⚠️  Mem0 未启用")
        return

    # 测试不同的用户 ID
    test_users = ["test_user", "<Mem0>", "default_user"]

    for user_id in test_users:
        print(f"\n{'='*60}")
        print(f"用户: {user_id}")
        print(f"{'='*60}")

        all_memories = manager.get_all_memories(user_id)

        if len(all_memories) == 0:
            print(f"⚠️  用户 '{user_id}' 没有任何记忆")
        else:
            print(f"✓ 共有 {len(all_memories)} 条记忆:")
            for i, mem in enumerate(all_memories, 1):
                print(f"  {i}. {mem.get('memory', 'N/A')}")

    print("\n" + "="*60)

if __name__ == "__main__":
    check_all_users()
