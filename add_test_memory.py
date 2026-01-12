"""
手动添加测试记忆
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import ConfigLoader
from src.memory.mem0_manager import Mem0Manager

def add_test_memory():
    """添加测试记忆"""
    print("\n" + "="*60)
    print("手动添加测试记忆")
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

    # 添加测试记忆
    print("\n[步骤 1] 添加测试记忆...")
    manager.add_conversation(
        user_input="我叫李明，是一名软件工程师，喜欢打篮球和看科幻电影",
        assistant_response="你好李明！很高兴认识你，我记住了你的信息",
        user_id=user_id
    )
    print("✓ 记忆已添加")

    # 等待一下让 Mem0 处理
    import time
    print("\n等待 Mem0 处理记忆...")
    time.sleep(2)

    # 检索记忆
    print("\n[步骤 2] 检索记忆...")
    queries = [
        "我是谁",
        "我的名字",
        "我的职业",
        "我的爱好"
    ]

    for query in queries:
        print(f"\n查询: '{query}'")
        results = manager.search_memories(query, user_id, limit=3)
        if results:
            print(f"  ✓ 检索到:\n{results}")
        else:
            print("  ⚠️  未检索到")

    # 获取所有记忆
    print("\n[步骤 3] 获取所有记忆...")
    all_memories = manager.get_all_memories(user_id)
    print(f"✓ 共有 {len(all_memories)} 条记忆:")
    for i, mem in enumerate(all_memories, 1):
        print(f"  {i}. {mem.get('memory', 'N/A')}")

    print("\n" + "="*60)
    print("提示：")
    print("现在可以运行 'python src/main.py' 启动程序")
    print("然后询问 '你知道我是谁吗？'")
    print("助手应该能记住你的信息了")
    print("="*60)

if __name__ == "__main__":
    add_test_memory()
