# ✅ 播放器问题已修复！

## 🔧 问题原因

之前使用 `ffplay` 从 stdin 读取 PCM 流时，会出现：
- **Broken pipe** 错误
- **提前退出** - ffplay 无法正确处理流式 PCM 输入
- **音频中断** - 无法连续播放

## 💡 解决方案

使用 **PyAudio** 替代 ffplay：

```python
import pyaudio

# 打开音频流
stream = audio.open(
    format=pyaudio.paInt16,  # 16-bit PCM
    channels=1,              # 单声道
    rate=24000,              # 24kHz
    output=True,
    frames_per_buffer=1024   # 小缓冲区，低延迟
)

# 直接写入音频数据
while True:
    audio_chunk = queue.get()
    stream.write(audio_chunk)  # 实时播放！
```

## ✅ 现在的效果

```
[播放器] PyAudio 流式播放已启动
[播放器] 首个音频块已播放
[播放器] 已播放 20 块
[播放器] 已播放 40 块
[播放器] 播放完成: 47 块, 960000 字节
```

**完全连贯，无中断！**

## 🚀 使用方法

### 1. 确保已安装 PyAudio

```bash
pip install pyaudio
```

### 2. 运行实时模式

```bash
python src/main.py
```

默认会自动使用 PyAudio 播放器。

### 3. 测试

```bash
python test_realtime.py
```

## 📊 性能对比

### ffplay (之前)
- ❌ Broken pipe 错误
- ❌ 音频中断
- ❌ 无法连续播放

### PyAudio (现在)
- ✅ 稳定播放
- ✅ 低延迟 (~50ms)
- ✅ 完全连贯
- ✅ 边接收边播放

## 🎯 完整流程

```
LLM 输出: "你" (10ms)
    ↓
TTS 接收: "你" → 开始合成
    ↓ (500ms)
音频块1: [20KB PCM] → PyAudio.write() → 扬声器播放
    ↓
LLM 输出: "好" (10ms)
    ↓
TTS 接收: "好" → 继续合成
    ↓ (100ms)
音频块2: [20KB PCM] → PyAudio.write() → 扬声器播放
    ↓
... 持续进行，完全连贯！
```

## 💡 技术细节

### PyAudio 优势

1. **直接写入音频设备** - 无需中间进程
2. **小缓冲区** - 降低延迟
3. **稳定可靠** - 专为流式音频设计
4. **跨平台** - macOS/Linux/Windows 都支持

### 缓冲区设置

```python
frames_per_buffer=1024  # 1024 samples
# 延迟 = 1024 / 24000 = 42.7ms
```

## 🎊 现在可以听到声音了！

运行：
```bash
python src/main.py
```

输入：
```
你: 请详细介绍一下人工智能
```

你会听到 AI **边说边播**，完全流畅连贯！🎉
