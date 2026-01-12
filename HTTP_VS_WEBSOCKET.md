# HTTP vs WebSocket vs 单向流 vs 双向流

## 一、HTTP vs WebSocket

### HTTP（超文本传输协议）

#### 特点
- **请求-响应模型**：客户端发送请求，服务器返回响应
- **无状态**：每次请求都是独立的
- **单向通信**：只能由客户端主动发起请求
- **短连接**：请求完成后连接关闭（HTTP/1.0）或复用（HTTP/1.1）

#### 工作流程
```
客户端                    服务器
  |                         |
  |-------- 请求 -------->  |
  |                         | (处理请求)
  |<------- 响应 --------- |
  |                         |
  连接关闭（或保持）
```

#### 优点
- ✅ 简单易用
- ✅ 广泛支持
- ✅ 适合一次性请求
- ✅ 有完善的缓存机制

#### 缺点
- ❌ 服务器无法主动推送
- ❌ 每次请求都有 HTTP 头开销
- ❌ 不适合实时通信
- ❌ 需要轮询来获取更新

#### 适用场景
- 普通网页浏览
- RESTful API
- 文件下载
- 一次性数据请求

#### 示例：TTS HTTP API
```python
import requests

# 发送请求
response = requests.post(
    "https://api.example.com/tts",
    json={"text": "你好"},
    headers={"Authorization": "Bearer token"}
)

# 等待完整响应
audio_data = response.content

# 保存音频
with open("output.mp3", "wb") as f:
    f.write(audio_data)
```

---

### WebSocket（Web 套接字）

#### 特点
- **全双工通信**：客户端和服务器可以同时发送和接收数据
- **持久连接**：连接建立后保持打开状态
- **低延迟**：无需重复建立连接
- **双向通信**：服务器可以主动推送数据

#### 工作流程
```
客户端                    服务器
  |                         |
  |---- HTTP 握手 -------> |
  |<--- 升级到 WS -------- |
  |                         |
  |<====== 持久连接 ======>|
  |                         |
  |-------- 消息 -------->  |
  |<------- 消息 --------- |
  |-------- 消息 -------->  |
  |<------- 消息 --------- |
  |         ...             |
```

#### 优点
- ✅ 实时双向通信
- ✅ 低延迟
- ✅ 减少网络开销（无重复 HTTP 头）
- ✅ 服务器可主动推送

#### 缺点
- ❌ 实现复杂
- ❌ 需要保持连接（消耗资源）
- ❌ 防火墙可能阻止
- ❌ 需要处理断线重连

#### 适用场景
- 实时聊天
- 在线游戏
- 实时数据推送
- 协作编辑
- **实时流式 TTS**

#### 示例：TTS WebSocket API
```python
import asyncio
import websockets

async def tts_websocket():
    # 建立 WebSocket 连接
    async with websockets.connect(
        "wss://api.example.com/tts",
        extra_headers={"Authorization": "Bearer token"}
    ) as websocket:

        # 发送文本（可以分多次发送）
        await websocket.send('{"text": "你"}')
        await websocket.send('{"text": "好"}')

        # 实时接收音频数据
        while True:
            audio_chunk = await websocket.recv()
            # 边接收边播放
            play_audio(audio_chunk)

            if is_finished(audio_chunk):
                break

asyncio.run(tts_websocket())
```

---

## 二、单向流 vs 双向流

### 单向流（Unidirectional Streaming）

#### 特点
- **单方向数据流**：数据只从一方流向另一方
- **可以是 HTTP 或 WebSocket**

#### 类型

##### 1. 服务器到客户端（Server → Client）
```
客户端                    服务器
  |                         |
  |-------- 请求 -------->  |
  |                         |
  |<------ 数据块 1 ------ |
  |<------ 数据块 2 ------ |
  |<------ 数据块 3 ------ |
  |<------ 数据块 4 ------ |
  |                         |
```

**示例**：
- HTTP 流式响应（SSE - Server-Sent Events）
- 视频流
- 文件下载
- **LLM 流式输出**

```python
# LLM 流式输出示例
for chunk in llm.chat_stream(messages):
    print(chunk, end="", flush=True)
    # 服务器 → 客户端（单向）
```

##### 2. 客户端到服务器（Client → Server）
```
客户端                    服务器
  |                         |
  |------ 数据块 1 -------> |
  |------ 数据块 2 -------> |
  |------ 数据块 3 -------> |
  |------ 数据块 4 -------> |
  |                         |
  |<------- 响应 --------- |
```

**示例**：
- 文件上传
- 音频录制上传

#### 优点
- ✅ 实现简单
- ✅ 适合单向数据传输
- ✅ HTTP 可以实现（SSE）

#### 缺点
- ❌ 无法同时双向传输
- ❌ 灵活性较低

---

### 双向流（Bidirectional Streaming）

#### 特点
- **双方向数据流**：客户端和服务器可以同时发送和接收数据
- **通常使用 WebSocket**
- **完全异步**：发送和接收独立进行

#### 工作流程
```
客户端                    服务器
  |                         |
  |====== 建立连接 ======> |
  |                         |
  |------ 数据块 1 -------> |
  |<----- 数据块 A ------- |
  |------ 数据块 2 -------> |
  |<----- 数据块 B ------- |
  |------ 数据块 3 -------> |
  |<----- 数据块 C ------- |
  |                         |
  同时发送和接收
```

#### 优点
- ✅ 真正的实时交互
- ✅ 最低延迟
- ✅ 灵活性最高
- ✅ 适合复杂交互

#### 缺点
- ❌ 实现最复杂
- ❌ 需要 WebSocket
- ❌ 需要处理并发

#### 适用场景
- 实时对话（边说边听）
- 在线游戏
- 协作编辑
- **实时语音对话（边输入边合成边播放）**

#### 示例：双向流式 TTS
```python
async def bidirectional_tts():
    async with websockets.connect("wss://api.example.com/tts") as ws:

        # 发送任务（异步）
        async def send_text():
            for char in "你好，学弟":
                await ws.send(f'{{"text": "{char}"}}')
                await asyncio.sleep(0.01)  # 逐字发送

        # 接收音频（异步）
        async def receive_audio():
            while True:
                audio_chunk = await ws.recv()
                play_audio(audio_chunk)  # 边接收边播放

        # 同时执行发送和接收
        await asyncio.gather(
            send_text(),
            receive_audio()
        )
```

---

## 三、对比总结

### 功能对比表

| 特性 | HTTP | WebSocket | 单向流 | 双向流 |
|------|------|-----------|--------|--------|
| **连接类型** | 短连接 | 长连接 | 取决于协议 | 长连接 |
| **通信方向** | 单向（请求-响应） | 双向 | 单向 | 双向 |
| **服务器推送** | ❌ | ✅ | ✅（单向） | ✅ |
| **实时性** | 低 | 高 | 中 | 高 |
| **延迟** | 高 | 低 | 中 | 最低 |
| **实现复杂度** | 简单 | 复杂 | 中等 | 最复杂 |
| **资源消耗** | 低 | 中 | 中 | 高 |
| **适合场景** | 一次性请求 | 实时交互 | 流式数据 | 实时双向交互 |

### 延迟对比

```
场景：用户说"你好"，AI 回复"你好，学弟"

┌─────────────────────────────────────────────────────────┐
│ HTTP（普通模式）                                         │
├─────────────────────────────────────────────────────────┤
│ 用户输入 → LLM 处理 → 等待完整响应 → TTS 合成 → 播放   │
│ [========================================] 3-5秒         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ HTTP + 单向流（流式模式）                                │
├─────────────────────────────────────────────────────────┤
│ 用户输入 → LLM 流式输出 → 按句 TTS → 播放               │
│ [===================] 1-2秒（首句）                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ WebSocket + 双向流（实时模式）                           │
├─────────────────────────────────────────────────────────┤
│ 用户输入 → LLM 逐字输出 → 实时 TTS → 边接收边播放       │
│ [==========] 0.5-1秒（首字）                             │
└─────────────────────────────────────────────────────────┘
```

---

## 四、在 TTS 中的应用

### 1. HTTP 普通模式

```python
# 等待完整响应
text = llm.chat("你好")  # 等待 2 秒
audio = tts.synthesize(text)  # 等待 1 秒
play(audio)  # 总延迟：3 秒
```

**特点**：
- 最简单
- 延迟最高
- 适合离线处理

---

### 2. HTTP 单向流模式

```python
# LLM 流式输出
for sentence in llm.chat_stream("你好"):
    # 每句话立即合成
    audio = tts.synthesize(sentence)
    play(audio)  # 首句延迟：1 秒
```

**特点**：
- 中等复杂度
- 延迟中等
- 适合实时对话

---

### 3. WebSocket 双向流模式

```python
# 真正的实时
async def realtime():
    # LLM 逐字输出
    async for char in llm.stream("你好"):
        # 立即发送给 TTS
        await tts_ws.send(char)

    # 同时接收音频
    async for audio_chunk in tts_ws.receive():
        play(audio_chunk)  # 首字延迟：0.5 秒
```

**特点**：
- 最复杂
- 延迟最低
- 最接近真人对话

---

## 五、你的项目中的实现

### 当前支持的模式

#### 1. 普通模式（HTTP）
```python
# src/main.py - chat_and_speak()
test.chat_and_speak("你好", tts_provider="qwen3")
```
- 使用 HTTP
- 等待完整响应
- 延迟：3-5 秒

#### 2. 流式模式（HTTP 单向流）
```python
# src/main.py - chat_and_speak_streaming()
test.chat_and_speak_streaming("你好", tts_provider="qwen3")
```
- LLM 使用 HTTP 流式
- TTS 按句处理
- 延迟：1-2 秒

#### 3. 实时模式（WebSocket 双向流）
```python
# src/main.py - chat_and_speak_realtime()
test.chat_and_speak_realtime("你好")
```
- LLM 使用 HTTP 流式
- TTS 使用 WebSocket 双向流
- 延迟：0.5-1 秒

---

## 六、如何选择

### 选择 HTTP
- ✅ 简单的一次性请求
- ✅ 不需要实时性
- ✅ 离线处理
- ✅ 文件下载/上传

### 选择 HTTP 单向流
- ✅ 需要流式输出（如 LLM）
- ✅ 中等实时性要求
- ✅ 实现相对简单
- ✅ 服务器推送数据

### 选择 WebSocket 双向流
- ✅ 需要真正的实时交互
- ✅ 双向通信
- ✅ 最低延迟
- ✅ 复杂的实时应用

---

## 七、火山引擎的选择

火山引擎官方示例使用 **WebSocket 双向流**：

```python
# 官方示例
wss://openspeech.bytedance.com/api/v3/tts/bidirection
```

**为什么选择双向流？**
1. 支持逐字输入（边输入边合成）
2. 支持实时音频输出（边合成边返回）
3. 最低延迟
4. 适合实时对话场景

**但这也是为什么实现复杂的原因！**

---

## 总结

| 模式 | 协议 | 流向 | 延迟 | 复杂度 | 适用场景 |
|------|------|------|------|--------|----------|
| **普通** | HTTP | 单向 | 高 | 低 | 离线处理 |
| **流式** | HTTP | 单向流 | 中 | 中 | 实时对话 |
| **实时** | WebSocket | 双向流 | 低 | 高 | 真人对话 |

希望这个解释清楚了！有什么不明白的可以继续问我。
