# AEC 回声消除设置指南

本指南将帮助你设置基于 WebRTC 的高质量回声消除（AEC）功能。

## 📋 前置要求

### 1. 下载 WebRTC 库文件

访问 [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi) 仓库，下载对应平台的 `libwebrtc_apm` 库文件：

- **macOS ARM64**: `src/webrtc_apm/macos/arm64/libwebrtc_apm.dylib`
- **macOS x64**: `src/webrtc_apm/macos/x64/libwebrtc_apm.dylib`
- **Windows x64**: `src/webrtc_apm/windows/x64/libwebrtc_apm.dll`

将文件放置到项目的对应目录。

### 2. 安装 BlackHole（仅 macOS）

BlackHole 是一个虚拟音频设备，用于捕获系统音频输出。

```bash
# 使用 Homebrew 安装
brew install blackhole-2ch
```

或者从官网下载：https://existential.audio/blackhole/

---

## 🎛️ 方案 1：硬件 AEC（推荐）✅

使用 macOS 聚合设备 + BlackHole，实现硬件级回声消除。

### 步骤 1：创建聚合设备

1. 打开 **音频 MIDI 设置**（Audio MIDI Setup）
   - 路径：`/Applications/Utilities/Audio MIDI Setup.app`
   - 或按 `Cmd + Space`，搜索 "Audio MIDI Setup"

2. 点击左下角的 **+** 按钮，选择 **创建聚合设备**（Create Aggregate Device）

3. 配置聚合设备：
   - ✅ 勾选你的**麦克风**（例如：MacBook Pro Microphone）
   - ✅ 勾选 **BlackHole 2ch**
   - 设置名称：`AEC Aggregate Device`

4. 设置时钟源（Clock Source）：
   - 选择你的麦克风作为时钟源（确保同步）

5. 点击 **应用**

### 步骤 2：查找设备索引

运行以下命令查看所有音频设备：

```bash
python list_audio_devices.py
```

找到你创建的聚合设备，记下它的索引号（例如：`设备 5`）。

### 步骤 3：启动程序

```bash
# 使用聚合设备启动（硬件 AEC）
python voice_to_voice.py --use-aggregate --device-index 5
```

**优点**：
- ✅ 硬件级同步，延迟可预测
- ✅ 参考信号准确，AEC 效果好
- ✅ 无需重采样，性能高

**缺点**：
- ⚠️ 需要手动配置聚合设备
- ⚠️ 仅支持 macOS

---

## 🔧 方案 2：软件 AEC（实验性）⚠️

不使用聚合设备，通过软件传递参考信号。

### 启动方式

```bash
# 启用软件 AEC（不推荐）
python voice_to_voice.py
```

**优点**：
- ✅ 无需配置聚合设备
- ✅ 简单易用

**缺点**：
- ⚠️ 时序不同步，效果不稳定
- ⚠️ 延迟不确定
- ⚠️ 需要重采样（24kHz → 16kHz）

**注意**：此方案已优化但仍不稳定，推荐使用方案 1 或方案 3。

---

## 🎧 方案 3：禁用 AEC + 使用耳机（最简单）✅

最稳定的方案，无需配置。

### 启动方式

```bash
# 禁用 AEC，使用耳机
python voice_to_voice.py --no-aec
```

**优点**：
- ✅ 最稳定
- ✅ 无需配置
- ✅ 延迟最低

**缺点**：
- ⚠️ 必须使用耳机
- ⚠️ 不能使用扬声器

---

## 🔍 故障排除

### 问题 1：找不到聚合设备

**解决方案**：
1. 确认已创建聚合设备
2. 运行 `python list_audio_devices.py` 查看设备列表
3. 确认设备索引正确

### 问题 2：AEC 效果不好

**可能原因**：
1. **流延迟设置不正确**：已优化为 40ms
2. **参考信号不准确**：使用聚合设备（方案 1）
3. **帧大小不匹配**：已优化为 10ms（160 samples）

**检查配置**：
```python
# 确认以下配置（已自动优化）
chunk_size = 160  # 10ms @ 16kHz
stream_delay_ms = 40  # 40ms 延迟
noise_level = MODERATE  # 中等噪声抑制
```

### 问题 3：回声仍然存在

**解决方案**：
1. 降低扬声器音量
2. 增加麦克风与扬声器的距离
3. 使用耳机（方案 3）

### 问题 4：声音被过度抑制

**解决方案**：
- 噪声抑制级别已设置为 MODERATE（中等）
- 如果仍然过度抑制，可以修改 `aec_processor.py:90`：
  ```python
  apm_config.noise_suppress.noise_level = 0  # LOW（低）
  ```

---

## 📊 性能对比

| 方案 | 稳定性 | 效果 | 延迟 | 配置难度 |
|------|--------|------|------|---------|
| 方案 1（硬件 AEC） | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 10ms | 中等 |
| 方案 2（软件 AEC） | ⭐⭐⭐ | ⭐⭐⭐ | 20ms | 简单 |
| 方案 3（耳机） | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 10ms | 简单 |

---

## 🎯 推荐方案

1. **首选**：方案 1（硬件 AEC）- 最佳效果
2. **备选**：方案 3（耳机）- 最简单
3. **实验**：方案 2（软件 AEC）- 仅供测试

---

## 📝 技术细节

### WebRTC AEC 优化配置

参考 py-xiaozhi 项目，本项目已优化以下配置：

1. **流延迟**：0ms → 40ms（考虑实际传播延迟）
2. **帧大小**：100ms → 10ms（WebRTC 标准）
3. **噪声抑制**：HIGH → MODERATE（避免过度抑制）
4. **Pipeline 频率**：16kHz（WebRTC 优化频率）
5. **增益控制**：自适应数字模式

### 关键参数说明

```python
# 流延迟（最关键）
set_stream_delay_ms(40)  # 40ms = 声波传播 + 硬件处理

# 帧大小
chunk_size = 160  # 10ms @ 16kHz（WebRTC 标准）

# 噪声抑制
noise_level = MODERATE  # 中等（避免切割语音）

# 处理顺序
process_reverse_stream(reference)  # 1. 先处理参考信号
process_stream(capture)            # 2. 再处理麦克风
```

---

## 🔗 参考资源

- [py-xiaozhi 项目](https://github.com/huangjunsen0406/py-xiaozhi)
- [BlackHole 官网](https://existential.audio/blackhole/)
- [WebRTC 文档](https://webrtc.org/)

---

## 💡 常见问题

**Q: 为什么需要 40ms 延迟？**

A: 声音从扬声器传播到麦克风需要时间（约 10-30ms），加上硬件处理延迟（约 10-20ms），总延迟约 40ms。

**Q: 可以使用其他虚拟音频设备吗？**

A: 可以，但推荐 BlackHole，因为它专为 macOS 优化，延迟低且稳定。

**Q: Windows/Linux 支持吗？**

A: 目前仅 macOS 支持 WebRTC AEC。Windows/Linux 建议使用耳机（方案 3）。

---

如有问题，请提交 Issue。
