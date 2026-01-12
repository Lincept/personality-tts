# LLM + TTS 语音助手

一个集成了大语言模型（LLM）和文本转语音（TTS）的实时语音助手系统。

## 功能特性

- ✅ **多 LLM 支持**：支持 OpenAI 兼容的 API（如 DeepSeek、Qwen 等）
- ✅ **多 TTS 支持**：支持 Qwen3 TTS、火山引擎 Seed2、MiniMax
- ✅ **实时流式对话**：LLM 逐字输出 → TTS 实时合成 → 边接收边播放
- ✅ **智能 Prompt 系统**：专为语音对话优化，控制输出格式
- ✅ **多角色支持**：默认助手、轻松助手、专业助手、陪伴助手
- ✅ **上下文管理**：用户信息、知识库、对话历史自动管理

## 项目结构

```
llm-tts-api-test/
├── config/
│   └── test_config.json       # 测试配置
├── src/
│   ├── audio/                 # 音频播放模块
│   │   ├── player.py          # 基础音频播放器
│   │   ├── streaming_player.py # 流式音频播放器（ffplay）
│   │   └── pyaudio_player.py  # 流式音频播放器（PyAudio）
│   ├── llm/
│   │   └── llm_client.py      # LLM 客户端封装
│   ├── tts/                   # TTS 客户端
│   │   ├── qwen3_tts.py       # 通义千问 TTS
│   │   ├── qwen3_realtime_tts.py # 通义千问实时 TTS
│   │   ├── volcengine_tts.py  # 火山引擎 Seed2
│   │   └── minimax_tts.py     # MiniMax TTS
│   ├── config_loader.py       # 配置加载器
│   ├── streaming_pipeline.py  # 流式处理管道
│   ├── realtime_pipeline.py   # 实时处理管道
│   ├── text_cleaner.py        # 文本清理工具
│   ├── voice_assistant_prompt.py # Prompt 管理系统
│   └── main.py                # 主程序
├── .env.example               # 环境变量示例
├── requirements.txt           # Python 依赖
├── README.md                  # 本文件
└── VOICE_ASSISTANT_PROMPT.md  # Prompt 系统详细文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制 `.env.example` 为 `.env`，填入你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# LLM API (OpenAI 兼容)
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# Qwen3 TTS
QWEN3_TTS_API_KEY=your_qwen3_key

# 火山引擎 Seed2 TTS
VOLCENGINE_APP_ID=your_app_id
VOLCENGINE_ACCESS_TOKEN=your_token

# MiniMax TTS
MINIMAX_API_KEY=your_minimax_key
MINIMAX_GROUP_ID=your_group_id
```

### 3. 运行语音助手

```bash
python src/main.py
```

或者明确指定交互模式：

```bash
python src/main.py interactive
```

## 使用指南

### 交互命令

启动后，你可以使用以下命令：

```
/quit                    # 退出程序
/mode                    # 切换模式 (realtime/streaming/normal)
/role <角色>             # 切换角色 (default/casual/professional/companion)
/clear                   # 清空对话历史
/history                 # 查看对话历史
/setname <名字>          # 设置用户名
/addknowledge <内容>     # 添加知识库
/info                    # 查看当前配置
```

### 示例对话

```
你: /role casual
✓ 已切换到角色: 轻松助手
  风格: 轻松聊天
  特点: 活泼、幽默、随和

你: /setname 小明
✓ 用户名已设置为: 小明

你: /addknowledge 喜欢攀岩
✓ 已添加知识: 喜欢攀岩

你: 推荐一些周末活动
助手: 小明你好！既然你喜欢攀岩，周末可以去攀岩馆练练手。要不要我推荐几个地方？

你: /info
当前配置:
  模式: 实时模式 (LLM逐字→TTS→边播边放) ⚡
  角色: 轻松助手 (活泼、幽默、随和)
  TTS: qwen3
  对话轮数: 1
  知识库条目: 1
```

## 三种对话模式

### 1. 实时模式（Realtime）⚡

**最快**，延迟最低：
- LLM 逐字输出
- TTS 实时接收并合成
- 音频边接收边播放

```python
# 仅支持 Qwen3 实时 TTS
test.chat_and_speak_realtime("你好")
```

### 2. 流式模式（Streaming）

**较快**，按句播放：
- LLM 流式输出
- 按句子分割
- 每句合成后立即播放

```python
test.chat_and_speak_streaming("你好", tts_provider="qwen3")
```

### 3. 普通模式（Normal）

**最稳定**，等待完整回复：
- 等待 LLM 完整回复
- 一次性合成
- 播放完整音频

```python
test.chat_and_speak("你好", tts_provider="qwen3")
```

## Prompt 系统

本项目包含专为语音对话优化的 Prompt 系统，详见 [VOICE_ASSISTANT_PROMPT.md](VOICE_ASSISTANT_PROMPT.md)。

### 核心特性

1. **输出格式控制**
   - 简洁回答（2-3 句话，最多 50 字）
   - 禁止 Markdown 格式
   - 禁止特殊符号和列表
   - 口语化表达

2. **多角色支持**
   - `default` - 默认助手（友好、专业、简洁）
   - `casual` - 轻松助手（活泼、幽默、随和）
   - `professional` - 专业助手（严谨、专业、高效）
   - `companion` - 陪伴助手（温暖、关心、耐心）

3. **上下文管理**
   - 用户信息（姓名、偏好、上下文）
   - 知识库（可添加自定义知识）
   - 对话历史（自动保留最近 10 轮）

### 使用示例

```python
from src.voice_assistant_prompt import VoiceAssistantPrompt

# 创建 Prompt 管理器
prompt = VoiceAssistantPrompt(role="casual")

# 设置用户信息
prompt.set_user_info(
    name="小明",
    preferences={"运动": "攀岩"}
)

# 添加知识
prompt.add_knowledge("用户是攀岩初学者", category="运动")

# 获取消息列表
messages = prompt.get_messages("推荐一些攀岩装备")

# 传递给 LLM
response = llm_client.chat(messages)
```

## 配置说明

### LLM 配置

支持任何 OpenAI 兼容的 API：

```env
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.deepseek.com  # 或其他兼容 API
OPENAI_MODEL=deepseek-chat                # 或其他模型
```

### TTS 配置

#### Qwen3 TTS（推荐用于实时模式）

```env
QWEN3_TTS_API_KEY=your_key
```

支持的音色：
- `Cherry` - 女声（默认）
- `Stella` - 女声
- `Bella` - 女声
- `Cindy` - 女声

#### 火山引擎 Seed2

```env
VOLCENGINE_APP_ID=your_app_id
VOLCENGINE_ACCESS_TOKEN=your_token
```

#### MiniMax

```env
MINIMAX_API_KEY=your_key
MINIMAX_GROUP_ID=your_group_id
```

## 技术架构

### 实时流式处理流程

```
用户输入
  ↓
LLM 流式生成 (逐字输出)
  ↓
实时 TTS (逐字接收，流式合成)
  ↓
流式音频播放 (边接收边播放)
  ↓
用户听到语音
```

### 关键技术

1. **流式处理**：使用 Python 生成器实现零延迟传递
2. **实时 TTS**：Qwen3 支持流式输入和输出
3. **流式播放**：PyAudio 或 ffplay 实现边接收边播放
4. **Prompt 优化**：专为语音场景设计，控制输出格式

## 依赖项

主要依赖：

```
openai>=1.0.0          # LLM 客户端
requests>=2.31.0       # HTTP 请求
python-dotenv>=1.0.0   # 环境变量
pyaudio>=0.2.13        # 音频播放（可选）
```

## 常见问题

### 1. PyAudio 安装失败

PyAudio 是可选依赖，如果安装失败，系统会自动使用 ffplay：

```bash
# macOS
brew install portaudio
pip install pyaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev
pip install pyaudio
```

### 2. 音频播放失败

确保系统安装了 ffplay：

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

### 3. LLM 输出仍包含 Markdown

Prompt 不是万能的，建议：
1. 降低 temperature 参数（0.7 左右）
2. 使用 `text_cleaner.py` 进行后处理
3. 尝试不同的模型

### 4. 实时模式延迟高

实时模式需要：
1. 稳定的网络连接
2. 低延迟的 LLM API
3. 支持流式的 TTS API（目前仅 Qwen3）

## 开发计划

- [ ] 支持更多 TTS 提供商
- [ ] 添加语音输入（STT）
- [ ] 支持多语言
- [ ] Web UI 界面
- [ ] 语音克隆功能

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请提交 Issue。
