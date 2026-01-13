#!/usr/bin/env python3
"""测试 WebRTC AEC 导入"""
import sys
import os

# 添加 src 目录到路径
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

print(f"Python 路径: {sys.path[:3]}")
print(f"src 目录: {src_dir}")

try:
    from webrtc_apm import WebRTCAudioProcessing, create_default_config
    print("✅ WebRTC 库导入成功")

    # 测试创建实例
    apm = WebRTCAudioProcessing()
    print("✅ WebRTC APM 实例创建成功")

    # 测试创建配置
    config = create_default_config()
    print("✅ 默认配置创建成功")

    print("\n🎉 所有测试通过！")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
