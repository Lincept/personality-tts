"""
检查当前用户的记忆状态
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import ConfigLoader
from src.memory.mem0_manager import Mem0Manager

def check_memories():
    """检查当前记忆"""
    print("\n" + "="*60)
    print("检查 Mem0 记忆状态")
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

    # 获取所有记忆
    print("\n[检查] 获取所有记忆...")
    all_memories = manager.get_all_memories(user_id)

    if len(all_memories) == 0:
        print("⚠️  当前用户没有任何记忆！")
        print("\n原因分析：")
        print("1. 这是第一次使用，还没有保存任何记忆")
        print("2. 或者之前的对话没有成功保存到 Mem0")
        print("\n建议：")
        print("1. 在对话中明确告诉助手你的信息，例如：")
        print("   '我叫张三，是一名程序员'")
        print("2. 然后退出程序，重新启动")
        print("3. 再次询问'你知道我是谁吗'，应该就能记住了")
    else:
        print(f"✓ 共有 {len(all_memories)} 条记忆:")
        for i, mem in enumerate(all_memories, 1):
            print(f"  {i}. {mem.get('memory', 'N/A')}")

        # 测试检索
        print("\n[检查] 测试记忆检索...")
        test_queries = [
            "我是谁",
            "我的名字",
            "关于我的信息"
        ]

        for query in test_queries:
            print(f"\n查询: '{query}'")
            results = manager.search_memories(query, user_id, limit=3)
            if results:
                print(f"  检索结果:\n{results}")
            else:
                print("  未检索到相关记忆")

    print("\n" + "="*60)

if __name__ == "__main__":
    check_memories()
