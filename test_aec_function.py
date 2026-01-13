#!/usr/bin/env python3
"""测试 AEC 功能"""
import sys
import os
import numpy as np

# 添加 src 目录到路径
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

from asr.aec_processor import SimpleAEC

print("=" * 60)
print("AEC 功能测试")
print("=" * 60)

# 创建 AEC 处理器
print("\n1. 创建 AEC 处理器...")
aec = SimpleAEC(sample_rate=16000)

# 生成测试信号
print("\n2. 生成测试信号...")
sample_rate = 16000
duration = 0.1  # 100ms
num_samples = int(sample_rate * duration)

# 生成 1000Hz 正弦波作为参考信号（扬声器输出）
t = np.linspace(0, duration, num_samples, False)
reference_signal = (np.sin(2 * np.pi * 1000 * t) * 10000).astype(np.int16)
print(f"   参考信号: {len(reference_signal)} 样本, RMS={np.sqrt(np.mean(reference_signal.astype(np.float32)**2)):.1f}")

# 生成混合信号（麦克风输入 = 参考信号 + 噪声）
noise = (np.random.randn(num_samples) * 1000).astype(np.int16)
mixed_signal = reference_signal + noise
print(f"   混合信号: {len(mixed_signal)} 样本, RMS={np.sqrt(np.mean(mixed_signal.astype(np.float32)**2)):.1f}")

# 添加参考信号
print("\n3. 添加参考信号到 AEC...")
aec.add_reference(reference_signal)

# 处理混合信号
print("\n4. 处理混合信号...")
processed_signal = aec.process(mixed_signal)
print(f"   处理后信号: {len(processed_signal)} 样本, RMS={np.sqrt(np.mean(processed_signal.astype(np.float32)**2)):.1f}")

# 计算回声消除效果
original_rms = np.sqrt(np.mean(mixed_signal.astype(np.float32) ** 2))
processed_rms = np.sqrt(np.mean(processed_signal.astype(np.float32) ** 2))
reduction = original_rms - processed_rms
reduction_percent = (reduction / original_rms * 100) if original_rms > 0 else 0

print("\n5. 回声消除效果:")
print(f"   原始 RMS: {original_rms:.1f}")
print(f"   处理后 RMS: {processed_rms:.1f}")
print(f"   消除量: {reduction:.1f} ({reduction_percent:.1f}%)")

# 关闭 AEC
print("\n6. 关闭 AEC...")
aec.close()

print("\n" + "=" * 60)
if reduction_percent > 10:
    print("✅ AEC 测试通过！回声消除正常工作")
else:
    print("⚠️ AEC 效果不明显，可能需要调整参数")
print("=" * 60)
