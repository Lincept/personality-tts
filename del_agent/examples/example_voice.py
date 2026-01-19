#!/usr/bin/env python3
"""
DEL Agent 语音交互示例
演示如何使用 DEL Agent 进行语音对话交互

版本：1.0.0
创建：2026-01-19
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from del_agent.frontend.voice_adapter import (
    VoiceAdapter,
    start_voice_conversation,
    check_audio_environment
)


async def main():
    """
    语音交互示例主函数
    
    演示功能：
    1. 检查音频环境
    2. 创建语音适配器
    3. 进行语音对话
    """
    
    print("=" * 60)
    print("DEL Agent 语音交互示例")
    print("=" * 60)
    print()
    
    # ====================================
    # Step 1: 检查音频环境
    # ====================================
    print("📝 Step 1: 检查音频环境...")
    
    env_status = check_audio_environment()
    
    print(f"   PyAudio 可用: {'✓' if env_status['pyaudio_available'] else '✗'}")
    print(f"   输入设备数量: {env_status['input_devices']}")
    print(f"   输出设备数量: {env_status['output_devices']}")
    
    if not env_status['pyaudio_available']:
        print()
        print("⚠ PyAudio 不可用，无法运行语音示例")
        print("安装方法:")
        print("  - Ubuntu/Debian: sudo apt-get install python3-pyaudio")
        print("  - macOS: brew install portaudio && pip install pyaudio")
        print("  - Windows: pip install pyaudio")
        return
    
    print()
    
    # ====================================
    # Step 2: 配置检查
    # ====================================
    print("📝 Step 2: 检查配置...")
    
    # 检查环境变量
    import os
    
    required_vars = [
        "VOLCENGINE_APP_ID",
        "VOLCENGINE_TOKEN", 
        "VOLCENGINE_CLUSTER_ID"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"   ⚠ 缺少环境变量: {', '.join(missing_vars)}")
        print()
        print("配置方法:")
        print("  1. 复制 env.example 为 .env")
        print("  2. 填写火山引擎语音服务的配置信息")
        print("  3. 运行: source .env")
        return
    
    print("   ✓ 配置完整")
    print()
    
    # ====================================
    # Step 3: 创建语音适配器
    # ====================================
    print("📝 Step 3: 创建语音适配器...")
    
    try:
        # 使用工厂方法创建语音适配器
        adapter = VoiceAdapter.create(
            mode="audio",  # 实时语音模式
            enable_aec=False  # 是否启用回声消除
        )
        
        print("   ✓ 语音适配器创建成功")
        print(f"   模式: {adapter.mode}")
        print()
    except Exception as e:
        print(f"   ✗ 创建失败: {e}")
        return
    
    # ====================================
    # Step 4: 交互模式选择
    # ====================================
    print("📝 Step 4: 选择交互模式")
    print("-" * 60)
    print("1. 实时语音对话（需要麦克风和扬声器）")
    print("2. 音频文件测试（使用示例音频文件）")
    print("3. 文本模拟测试（使用文本模拟语音）")
    print()
    
    choice = input("请选择模式 (1/2/3，默认3): ").strip() or "3"
    print()
    
    # ====================================
    # Step 5: 执行对应的交互
    # ====================================
    if choice == "1":
        # 实时语音对话
        print("📝 Step 5: 开始实时语音对话")
        print("-" * 60)
        print("提示：说话时会自动识别并回复")
        print("提示：按 Ctrl+C 结束对话")
        print()
        
        try:
            await adapter.start_conversation(user_id="demo_user")
        except KeyboardInterrupt:
            print("\n\n对话已结束")
    
    elif choice == "2":
        # 音频文件测试
        print("📝 Step 5: 音频文件测试")
        print("-" * 60)
        
        audio_file = input("请输入音频文件路径: ").strip()
        
        if not audio_file or not Path(audio_file).exists():
            print(f"✗ 文件不存在: {audio_file}")
            return
        
        # 创建音频文件模式的适配器
        file_adapter = VoiceAdapter.create(
            mode="audio_file",
            audio_file=audio_file
        )
        
        print(f"\n处理音频文件: {audio_file}")
        
        try:
            await file_adapter.start_conversation(user_id="demo_user")
            print("✓ 音频文件处理完成")
        except Exception as e:
            print(f"✗ 处理失败: {e}")
    
    else:
        # 文本模拟测试
        print("📝 Step 5: 文本模拟测试")
        print("-" * 60)
        
        # 创建文本模式的适配器
        text_adapter = VoiceAdapter.create(mode="text")
        
        print("提示：输入文本进行模拟对话")
        print("提示：输入 'quit' 或 'exit' 结束")
        print()
        
        while True:
            user_input = input("用户: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            try:
                # 处理文本输入
                response = await text_adapter.process_text(
                    user_id="demo_user",
                    text=user_input
                )
                
                print(f"助手: {response}")
                print()
            
            except Exception as e:
                print(f"[错误] {e}")
    
    print()
    print("=" * 60)
    print("示例完成！")
    print("=" * 60)


def quick_test():
    """
    快速测试（不需要音频环境）
    """
    print("=" * 60)
    print("DEL Agent 语音适配器快速测试")
    print("=" * 60)
    print()
    
    print("测试 1: 环境检查")
    env = check_audio_environment()
    print(f"  PyAudio: {'可用' if env['pyaudio_available'] else '不可用'}")
    print()
    
    print("测试 2: 文本模式创建")
    try:
        adapter = VoiceAdapter.create(mode="text")
        print(f"  ✓ 创建成功，模式: {adapter.mode}")
    except Exception as e:
        print(f"  ✗ 创建失败: {e}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # 快速测试模式
        quick_test()
    else:
        # 完整示例
        asyncio.run(main())
