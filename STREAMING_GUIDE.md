# 🚀 流式处理功能说明

## ✨ 新功能：真正的流式处理

现在支持 **LLM 流式输出 → TTS 实时合成 → 边生成边播放**！

### 🎯 工作原理

```
LLM 流式输出文本
    ↓
按句子分割（智能断句）
    ↓
每个句子立即送入 TTS
    ↓
TTS 流式生成音频
    ↓
边生成边播放
```

### ⚡ 速度对比

**非流式模式（旧）：**
1. 等待 LLM 生成完整回复（10-30秒）
2. 等待 TTS 转换全部文本（5-15秒）
3. 开始播放

总延迟：**15-45秒**

**流式模式（新）：**
1. LLM 生成第一句话（1-3秒）
2. TTS 立即转换第一句（1-2秒）
3. 立即开始播放
4. 后续句子并行处理

首句延迟：**2-5秒** ⚡

## 🎮 使用方法

### 1. 交互模式（默认流式）

```bash
python src/main.py
```

启动后默认使用流式模式：

```
当前TTS提供商: qwen3
当前模式: 流式

你: 你好，请介绍一下你自己
```

### 2. 切换模式

在交互模式中输入：

```
/streaming
```

可以在流式和非流式模式之间切换。

### 3. 编程调用

```python
from src.main import LLMTTSTest

test = LLMTTSTest()

# 流式处理
test.chat_and_speak_streaming(
    prompt="你好，请介绍一下你自己",
    tts_provider="qwen3"
)

# 非流式处理（旧方式）
test.chat_and_speak(
    prompt="你好",
    tts_provider="qwen3",
    stream=True
)
```

## 📊 流式处理特点

### ✅ 优点

1. **响应更快**：首句延迟降低 80%
2. **体验更好**：边说边播，更自然
3. **并行处理**：LLM、TTS、播放同时进行
4. **资源高效**：不需要等待完整生成

### ⚠️ 注意事项

1. **断句逻辑**：
   - 按句号、问号、感叹号分句
   - 最小句子长度：10 字符
   - 最大句子长度：100 字符
   - 过长自动在逗号处分割

2. **音频文件**：
   - 每个句子生成独立的音频文件
   - 文件名格式：`stream_时间戳_序号.wav`
   - 播放完成后可以删除或保留

3. **错误处理**：
   - 某个句子 TTS 失败不影响其他句子
   - 会在控制台显示错误信息

## 🎤 支持的 TTS 服务

目前流式处理支持：

- ✅ **Qwen3 TTS** - 完全支持流式
- ⏳ **火山引擎 Seed2** - 待测试
- ⏳ **MiniMax** - 待测试

## 🔧 高级配置

### 调整断句参数

编辑 `src/streaming_pipeline.py`：

```python
splitter = BufferedSentenceSplitter(
    min_length=10,   # 最小句子长度
    max_length=100   # 最大句子长度
)
```

### 自定义处理逻辑

```python
from src.streaming_pipeline import StreamingPipeline

pipeline = StreamingPipeline()

# 自定义句子回调
def on_sentence(sentence):
    print(f"[处理中] {sentence}")
    # 可以添加自定义逻辑

pipeline.run(
    text_stream=llm_stream,
    tts_client=tts,
    audio_player=player,
    output_dir="data/audios",
    on_sentence=on_sentence
)
```

## 🎯 使用建议

### 适合流式的场景

- ✅ 长文本回复（>50字）
- ✅ 对话交互
- ✅ 实时播报
- ✅ 语音助手

### 适合非流式的场景

- ✅ 短文本（<20字）
- ✅ 需要完整音频文件
- ✅ 批量处理
- ✅ 对比测试

## 🐛 故障排除

### 问题：音频播放卡顿

**原因**：TTS 生成速度慢于播放速度

**解决**：
- 增加最小句子长度（给 TTS 更多时间）
- 使用更快的 TTS 服务

### 问题：断句不准确

**原因**：文本没有明显的句子结束符

**解决**：
- 调整 `min_length` 和 `max_length`
- 在 prompt 中要求 AI 使用标点符号

### 问题：某些句子没有播放

**原因**：TTS 合成失败

**解决**：
- 查看控制台错误信息
- 检查 API 配额和网络连接

## 📈 性能优化

### 1. 并发处理

流式管道使用 3 个线程：
- 文本生产者（LLM 输出）
- TTS 处理器（音频合成）
- 音频播放器（播放音频）

### 2. 队列缓冲

- 文本队列：缓存待处理的句子
- 音频队列：缓存待播放的音频

### 3. 智能断句

- 避免过短的句子（减少 API 调用）
- 避免过长的句子（降低延迟）
- 在标点处自然分割

## 🎊 开始使用

```bash
# 启动流式交互模式
python src/main.py

# 输入问题
你: 请给我讲一个故事

# 享受实时语音播放！
```

体验真正的实时 AI 语音对话！🚀
