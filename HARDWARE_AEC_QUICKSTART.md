# 硬件 AEC 快速开始指南

## 🎯 目标

使用聚合设备实现稳定的 AEC（回声消除），像 python3.7 项目一样。

## 📋 步骤

### 1. 安装 BlackHole

```bash
brew install blackhole-2ch
```

或从官网下载：https://existential.audio/blackhole/

### 2. 创建聚合设备

1. 打开"应用程序" → "实用工具" → "音频 MIDI 设置"
2. 点击左下角"+"号 → "创建聚合设备"
3. 勾选以下设备（**顺序很重要**）：
   - ✅ **第一个**：MacBook Air 麦克风（或你的麦克风）
   - ✅ **第二个**：BlackHole 2ch
4. 设置采样率：16000 Hz
5. 重命名为："AEC Aggregate Device"

### 3. 创建多输出设备

1. 点击左下角"+"号 → "创建多输出设备"
2. 勾选以下设备：
   - ✅ MacBook Air 扬声器（或你的扬声器）
   - ✅ BlackHole 2ch
3. 重命名为："AEC Multi-Output Device"

### 4. 系统音频设置

1. 打开"系统设置" → "声音"
2. **输出**：选择"AEC Multi-Output Device"
3. **输入**：保持默认（不要选聚合设备）

### 5. 查找设备索引

```bash
python list_audio_devices.py
```

找到聚合设备的索引（标记为 ⭐），例如：`设备索引: 2`

### 6. 启动程序

```bash
python voice_to_voice.py --use-aggregate --device-index 2
```

（将 `2` 替换为你的聚合设备索引）

## 🎉 完成！

现在你可以外放使用，AEC 会自动消除回声。

## 📊 预期效果

```
[AEC] 麦克风: 150.0, 参考: 5000.0 → 处理后: 15.0 (消除: 135.0, 90.0%)
```

- 麦克风：原始麦克风音量
- 参考：BlackHole 捕获的扬声器输出
- 处理后：AEC 处理后的音量
- 消除：回声消除量和百分比

## 🔧 故障排除

### 问题 1：找不到聚合设备

```bash
python voice_to_voice.py --list-devices
```

查看所有设备，确认聚合设备存在。

### 问题 2：只有 1 个通道

确认聚合设备中同时勾选了麦克风和 BlackHole。

### 问题 3：没有声音

确认系统输出设置为"多输出设备"。

### 问题 4：仍有回声

1. 降低扬声器音量
2. 调整 AEC 延迟参数（编辑 `src/asr/aec_processor.py`）
3. 使用耳机（最可靠）

## 💡 使用方式对比

| 方式 | 命令 | 稳定性 | 效果 | 配置 |
|------|------|--------|------|------|
| 禁用 AEC + 耳机 | `python voice_to_voice.py --no-aec` | ✅ 100% | ✅ 100% | ✅ 简单 |
| 硬件 AEC（聚合设备） | `python voice_to_voice.py --use-aggregate --device-index 2` | ✅ 稳定 | ✅ 90%+ | ⚠️ 中等 |
| 软件 AEC（已弃用） | `python voice_to_voice.py` | ❌ 不稳定 | ⚠️ 74% | ✅ 简单 |

## 🎓 工作原理

```
你说话 → 麦克风 → 聚合设备通道 0
                        ↓
                   WebRTC AEC ← 参考信号
                        ↓
                   处理后音频 → ASR

AI 说话 → 扬声器 → 多输出设备 → BlackHole → 聚合设备通道 1
```

**关键点**：
- 所有数据在同一个音频流中
- 单线程处理，无并发问题
- 与 python3.7 项目相同的架构

## 📚 相关文档

- `HARDWARE_AEC_SETUP.md` - 详细配置说明
- `list_audio_devices.py` - 设备列表工具
- `AEC_STATUS.md` - AEC 状态说明

## ✅ 推荐方案

1. **首选**：禁用 AEC + 耳机（最简单、最可靠）
2. **次选**：硬件 AEC（聚合设备）（需要配置，但效果好）
3. **不推荐**：软件 AEC（不稳定）
