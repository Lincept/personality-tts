#!/usr/bin/env python3
"""
列出所有音频设备，帮助找到聚合设备的索引
"""
import pyaudio

def list_audio_devices():
    """列出所有音频设备"""
    p = pyaudio.PyAudio()

    print("\n" + "=" * 80)
    print("音频设备列表")
    print("=" * 80)

    print("\n【输入设备】（麦克风）")
    print("-" * 80)

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"\n设备索引: {i}")
            print(f"名称: {info['name']}")
            print(f"输入通道数: {info['maxInputChannels']}")
            print(f"采样率: {int(info['defaultSampleRate'])} Hz")

            # 标记聚合设备
            if 'Aggregate' in info['name'] or 'aggregate' in info['name'].lower():
                print("⭐ 这是聚合设备！")
                if info['maxInputChannels'] >= 2:
                    print(f"   ✅ 有 {info['maxInputChannels']} 个通道，可以用于硬件 AEC")
                else:
                    print("   ⚠️ 只有 1 个通道，无法用于硬件 AEC")

    print("\n" + "-" * 80)
    print("\n【输出设备】（扬声器）")
    print("-" * 80)

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxOutputChannels'] > 0:
            print(f"\n设备索引: {i}")
            print(f"名称: {info['name']}")
            print(f"输出通道数: {info['maxOutputChannels']}")
            print(f"采样率: {int(info['defaultSampleRate'])} Hz")

            # 标记多输出设备
            if 'Multi-Output' in info['name'] or 'multi' in info['name'].lower():
                print("⭐ 这是多输出设备！")

    print("\n" + "=" * 80)
    print("\n使用说明：")
    print("1. 找到聚合设备的索引（标记为 ⭐）")
    print("2. 确认它有 2 个或更多输入通道")
    print("3. 使用该索引启动程序：")
    print("   python voice_to_voice.py --device-index <索引> --use-aggregate")
    print("\n例如：")
    print("   python voice_to_voice.py --device-index 2 --use-aggregate")
    print("=" * 80 + "\n")

    p.terminate()

if __name__ == '__main__':
    list_audio_devices()
