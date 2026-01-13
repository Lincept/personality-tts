# 快速开始指南

## 5 分钟上手

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `.env` 文件：

```bash
# 必需：DashScope API Key（用于 ASR 和 TTS）
QWEN3_API_KEY=sk-your-api-key-here

# 必需：LLM API Key
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# 可选：启用长期记忆
ENABLE_MEM0=true
```

### 3. 选择模式运行

#### 模式 1: 文字对话（推荐新手）

```bash
python text_to_speech.py
```

然后输入文字，AI 会朗读回复。

#### 模式 2: 语音对话

```bash
python voice_to_voice.py
```

对着麦克风说话，AI 会语音回复。

**注意**：
- 需要麦克风权限
- 建议使用耳机

## 常用命令

在文字对话模式中：

```
/quit              - 退出
/role casual       - 切换到轻松助手
/clear             - 清空对话历史
/memories          - 查看记忆
/help              - 查看所有命令
```

## 故障排除

### macOS 麦克风权限

```
系统设置 → 隐私与安全性 → 麦克风 → 允许终端
```

### PyAudio 安装失败

```bash
brew install portaudio
pip install pyaudio
```

## 更多信息

- 详细文档：[README.md](README.md)
- 更新日志：[CHANGELOG.md](CHANGELOG.md)
