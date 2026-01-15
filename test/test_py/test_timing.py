"""
性能监控功能测试脚本
测试计时器是否正常工作，不会导致内存错误
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.timing_utils import ConversationTimer

def test_basic_timing():
    """测试基本计时功能"""
    print("测试 1: 基本计时功能")
    timer = ConversationTimer(enable=True)

    timer.start_conversation()

    with timer.time("测试环节1"):
        import time
        time.sleep(0.1)

    with timer.time("测试环节2"):
        time.sleep(0.2)

    timer.print_summary()
    print("✅ 测试 1 通过\n")

def test_disabled_timing():
    """测试禁用计时功能"""
    print("测试 2: 禁用计时功能")
    timer = ConversationTimer(enable=False)

    timer.start_conversation()

    with timer.time("测试环节1"):
        import time
        time.sleep(0.1)

    timer.print_summary()
    print("✅ 测试 2 通过（应该没有输出）\n")

def test_generator_timing():
    """测试生成器中的计时（不使用上下文管理器）"""
    print("测试 3: 生成器中的计时")
    timer = ConversationTimer(enable=True)

    timer.start_conversation()

    def simple_generator():
        """简单的生成器"""
        for i in range(3):
            yield f"消息 {i}"

    # 模拟 pipeline.run 中的计时方式
    import time
    start = time.time()
    for chunk in simple_generator():
        print(chunk)
        time.sleep(0.1)
    duration = time.time() - start

    # 手动记录统计
    timer.stats["生成器"] = type('obj', (object,), {
        'duration': duration,
        'name': '生成器'
    })

    timer.print_summary()
    print("✅ 测试 3 通过\n")

if __name__ == "__main__":
    print("=" * 60)
    print("性能监控功能测试")
    print("=" * 60)
    print()

    try:
        test_basic_timing()
        test_disabled_timing()
        test_generator_timing()

        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
