#!/usr/bin/env python3
"""
测试 BlackHole 是否能捕获到音频
"""
import pyaudio
import numpy as np
import time

def test_blackhole():
    """测试 BlackHole 捕获"""
    p = pyaudio.PyAudio()

    # 找到 BlackHole 设备
    blackhole_index = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if 'BlackHole' in info['name'] and info['maxInputChannels'] > 0:
            blackhole_index = i
            print(f"✅ 找到 BlackHole: 设备 {i} - {info['name']}")
            print(f"   输入通道数: {info['maxInputChannels']}")
            print(f"   采样率: {int(info['defaultSampleRate'])} Hz")
            break

    if blackhole_index is None:
        print("❌ 未找到 BlackHole 设备")
        p.terminate()
        return

    print("\n" + "=" * 80)
    print("开始监听 BlackHole...")
    print("请播放一些音频（音乐、视频等）")
    print("按 Ctrl+C 停止")
    print("=" * 80 + "\n")

    # 打开 BlackHole 输入流
    stream = p.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=48000,
        input=True,
        input_device_index=blackhole_index,
        frames_per_buffer=1600
    )

    try:
        counter = 0
        while True:
            # 读取音频数据
            data = stream.read(1600, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.int16)

            # 计算音量
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))

            counter += 1
            if counter % 10 == 0:  # 每 10 次打印一次
                if rms > 100:
                    print(f"✅ BlackHole 音量: {rms:.1f} (有音频)")
                else:
                    print(f"⚠️ BlackHole 音量: {rms:.1f} (静音)")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n停止监听")

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("BlackHole 音频捕获测试")
    print("=" * 80 + "\n")

    print("⚠️ 重要提示：")
    print("1. 确保系统音频输出设置为'多输出设备'")
    print("2. 确保多输出设备中勾选了扬声器和 BlackHole")
    print("3. 播放一些音频来测试\n")

    test_blackhole()
