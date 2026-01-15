# Personality TTS - 个性化语音助手

一个集成了**语音识别（ASR）**、**大语言模型（LLM）**、**文本转语音（TTS）** 和 **长期记忆（Mem0）** 的实时语音助手系统。

## ✨ 功能特性

### 核心功能
- 🎤 **实时语音识别**：使用阿里云 DashScope Paraformer 实时识别
- 🤖 **智能对话**：支持 OpenAI 兼容的 LLM API（Qwen、DeepSeek 等）
- 🔊 **实时语音合成**：支持 Qwen3 TTS、火山引擎 Seed2
- 🧠 **长期记忆**：使用 Mem0 记住用户信息和对话历史
- ⚡ **语音打断**：类似打电话的自然交互体验
- 🎛️ **AEC 回声消除**：基于 WebRTC 的高质量回声消除（新增）

### 两种使用模式
1. **文字对话模式**：你打字，AI 说话（带语音朗读）
2. **语音对话模式**：你说话，AI 说话（全语音交互）

### 技术特点
- ✅ **全流式处理**：LLM 流式输出 → TTS 实时合成 → 边接收边播放
- ✅ **智能 Prompt**：专为语音对话优化，控制输出格式
- ✅ **多角色支持**：默认助手、专业助手、陪伴助手等
- ✅ **上下文管理**：自动管理用户信息、知识库、对话历史

## 📁 项目结构

```
personality-tts/
├── src/
│   ├── asr/                    # 语音识别模块
│   │   ├── dashscope_asr.py    # DashScope ASR 客户端
│   │   ├── audio_input.py      # 麦克风音频输入
│   │   ├── interrupt_controller.py # 语音打断控制器
│   │   └── aec_processor.py   # AEC 回声消除处理器
│   ├── memory/                 # 记忆模块
│   │   └── mem0_manager.py     # Mem0 记忆管理器
│   ├── audio/                  # 音频播放模块
│   │   ├── player.py           # 基础播放器
│   │   ├── streaming_player.py # 流式播放器（ffplay）
│   │   └── pyaudio_player.py   # 流式播放器（PyAudio）
│   ├── llm/
│   │   └── llm_client.py       # LLM 客户端
│   ├── tts/                    # TTS 客户端
│   │   ├── qwen3_realtime_tts.py # 通义千问实时 TTS
│   │   └── volcengine_realtime_tts.py # 火山引擎实时 TTS
│   ├── streaming_pipeline.py   # 流式处理管道
│   ├── realtime_pipeline.py    # 实时处理管道
│   ├── voice_assistant_prompt.py # Prompt 管理系统
│   └── main.py                 # 主程序（统一入口）
├── .env                        # 环境变量配置
└── README.md                   # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `dashscope` - 阿里云 DashScope SDK（ASR + TTS）
- `openai` - OpenAI SDK（LLM）
- `pyaudio` - 音频输入/输出
- `mem0ai` - 长期记忆管理

### 2. 下载 WebRTC AEC 库文件（可选）

如果需要使用 AEC（回声消除）功能，需要下载 WebRTC 库文件：

1. 访问 [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi) 仓库
2. 下载对应平台的 `libwebrtc_apm` 库文件
3. 将文件放置到 `src/webrtc_apm/` 目录下对应的平台文件夹：
   - macOS ARM64: `src/webrtc_apm/macos/arm64/libwebrtc_apm.dylib`
   - macOS x64: `src/webrtc_apm/macos/x64/libwebrtc_apm.dylib`
   - Windows x64: `src/webrtc_apm/windows/x64/libwebrtc_apm.dll`

**注意**：AEC 功能目前不稳定，推荐使用 `--no-aec` 参数 + 耳机的方式。

### 3. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
# DashScope API Key（用于 ASR 和 TTS）
QWEN3_API_KEY=sk-your-api-key-here

# LLM API Key
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# Mem0 记忆管理
ENABLE_MEM0=true
MEM0_USER_ID=your_user_id
```

### 4. 命令行参数说明

#### Python 模块运行参数 `-m`

**作用**：将 Python 文件作为模块来运行

**推荐使用 `-m` 的原因**：
- ✅ 模块导入更可靠
- ✅ 符合 Python 最佳实践
- ✅ 更好地处理模块导入路径

**对比**：
```bash
# 方式 1：直接运行（不推荐）
python3 src/main.py --role natural

# 方式 2：使用 -m 参数（推荐）
python3 -m src.main --role natural
```

#### 角色参数 `--role`

**作用**：指定 AI 助手的个性、说话风格和行为特征

**不加 `--role` 的效果**：
- 📋 会显示角色选择菜单
- 🎯 需要交互式选择角色
- 🔄 每次启动都需要选择

**加 `--role` 的效果**：
- ✅ 直接使用指定的角色
- ✅ 快速启动，无需选择
- ✅ 适合已确定角色的场景

#### 可用角色列表

📖 **详细角色说明**：[docs/roles.md](docs/roles.md) - 查看所有角色的详细说明和使用示例

### 4. 运行

📖 **快速开始指南**：[docs/快速开始.md](docs/快速开始.md) - 30 秒快速上手！

所有功能通过统一的入口 `src/main.py` 运行，使用命令行参数控制模式。

#### 查看帮助

```bash
python3 -m src.main --help
```

#### 模式 1: 文字对话（你打字，AI 说话）

```bash
# 默认模式（会提示选择角色）
python3 -m src.main

# 指定角色 - 自然助手
python3 -m src.main --role natural

# 指定角色 - 学姐助手
python3 -m src.main --role xuejie

# 指定角色 - 幽默助手
python3 -m src.main --role funny

# 显式指定文字模式
python3 -m src.main --text
```

功能：
- 输入文字，AI 会朗读回复
- 支持实时流式 TTS
- 支持多种命令（/quit, /role, /clear 等）

#### 模式 2: 语音对话（你说话，AI 说话）

```bash
# 推荐方式：禁用 AEC + 使用耳机（最稳定）
python3 -m src.main --voice --no-aec

# 指定角色 - 学姐助手 + 耳机模式
python3 -m src.main --voice --no-aec --role xuejie

# 指定角色 - 自然助手 + 耳机模式
python3 -m src.main --voice --no-aec --role natural

# 实验性：启用 AEC（需要聚合设备）
python3 -m src.main --voice --device-index <聚合设备索引>

# 指定 ASR 模型 - Paraformer v2（默认）
python3 -m src.main --voice --no-aec --asr-model paraformer-realtime-v2

# 指定 ASR 模型 - FunASR 2025
python3 -m src.main --voice --no-aec --asr-model fun-asr-realtime-2025-11-07

# 组合使用：AEC + 指定角色 + 指定 ASR 模型
python3 -m src.main --voice --device-index <索引> --role xuejie --asr-model paraformer-realtime-v2
```

功能：
- 对着麦克风说话，AI 会语音回复
- 支持语音打断（说话时自动停止 AI 播放）
- 全流式处理，低延迟

**注意**：
- 需要麦克风权限
- **强烈推荐使用耳机**（避免回声）
- macOS 需要在"系统设置 → 隐私与安全性 → 麦克风"中授权
- AEC 功能已优化，参考 py-xiaozhi 实现
- 详细 AEC 设置指南：[AEC_SETUP_GUIDE.md](AEC_SETUP_GUIDE.md)

#### 工具命令

```bash
# 列出所有音频设备
python3 -m src.main --list-devices

# 检查 ASR 鉴权
python3 -m src.main --check-asr
```

## 📝 使用说明

### 文字对话模式命令

在文字对话模式中，支持以下命令：

```
/quit              - 退出程序
/mode              - 切换模式（realtime/streaming/normal）
/provider          - 切换 TTS 提供商（qwen3/volcengine）
/role <角色>       - 切换角色
/clear             - 清空对话历史
/history           - 查看对话历史
/setname <名字>    - 设置用户名
/memories          - 查看长期记忆
/clearmem          - 清除长期记忆
/info              - 查看当前配置
```

### 语音对话模式

1. 启动程序后，等待提示 `[等待你说话...]`
2. 对着麦克风说话
3. AI 会自动识别并回复
4. 在 AI 说话时，你可以直接开始说话打断它
5. 按 `Ctrl+C` 退出

### 退出命令

在语音对话模式中，可以通过以下命令退出：

```
退出
再见
拜拜
结束对话
关闭程序
```

## 🧠 长期记忆功能

系统使用 Mem0 自动记住：
- 用户的个人信息（姓名、偏好等）
- 重要的对话内容
- 用户的习惯和兴趣

查看记忆：
```
/memories
```

清除记忆：
```
/clearmem
```

## 🎯 功能说明

### 1. 语音识别模块（ASR）
- **位置**：`src/asr/`
- **功能**：
  - 实时语音识别（DashScope Paraformer）
  - 麦克风音频输入
  - 语音打断控制
- **文件**：
  - `dashscope_asr.py` - ASR 客户端
  - `audio_input.py` - 麦克风录音
  - `interrupt_controller.py` - 打断控制器

### 2. 长期记忆模块（Mem0）
- **位置**：`src/memory/`
- **功能**：
  - 自动提取和存储重要信息
  - 基于上下文检索相关记忆
  - 支持多用户记忆隔离
- **文件**：
  - `mem0_manager.py` - Mem0 管理器

### 3. AEC 回声消除
- **位置**：`src/asr/aec_processor.py`, `src/webrtc_apm/`
- **功能**：
  - 基于 WebRTC 的高质量回声消除
  - 自动捕获扬声器输出作为参考信号
  - 实时处理，无明显延迟
  - 内置噪声抑制和高通滤波
- **支持平台**：macOS ARM64（其他平台需重新编译）
- **详细文档**：参见 [AEC_INTEGRATION.md](AEC_INTEGRATION.md)

### 4. 语音对话模式
- **位置**：`src/main.py` 中的 `VoiceInteractiveMode` 类
- **功能**：
  - 全语音交互（ASR + LLM + TTS）
  - 语音打断（Barge-in）
  - 实时流式处理
  - 集成 AEC 回声消除

### 5. 打断机制
- **功能**：
  - 检测用户说话时自动停止 AI 播放
  - LLM 停止生成，节省 API 成本
  - 被打断的对话不保存到历史
- **实现**：
  - 在 `VoiceInteractiveMode` 类中实现
  - 使用 `InterruptController` 检测打断
  - 通过 `pipeline.stop()` 停止 LLM 和 TTS

## ⚙️ 配置说明

### LLM 配置

支持任何 OpenAI 兼容的 API：

```bash
# 通义千问
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# DeepSeek
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# OpenAI
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

### TTS 配置

支持两种 TTS 提供商：

1. **Qwen3 TTS**（推荐）
   - 首包延迟：~200ms
   - 音质：优秀
   - 支持多种音色

2. **火山引擎 Seed2**
   - 首包延迟：~300ms
   - 音质：优秀
   - 需要单独申请 API

### Mem0 配置

```bash
# 启用 Mem0（可选）
ENABLE_MEM0=true

# 用户 ID（用于区分不同用户）
MEM0_USER_ID=your_user_id

# Mem0 使用的 LLM（用于记忆提取/Embedding）
# - 如果不设置 MEM0_LLM_*，会自动回退使用 OPENAI_*（openai_compatible）
MEM0_LLM_API_KEY=your_openai_api_key_here
MEM0_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MEM0_LLM_MODEL=qwen-plus

# 可选：启用知识图谱（Neo4j）
ENABLE_GRAPH=false
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

## 🔧 故障排除

### 麦克风无权限

**macOS**:
```
系统设置 → 隐私与安全性 → 麦克风 → 允许终端/Python
```

### PyAudio 安装失败

**macOS**:
```bash
brew install portaudio
pip install pyaudio
```

**Linux**:
```bash
sudo apt-get install portaudio19-dev
pip install pyaudio
```

### 语音识别延迟高

1. 检查网络连接
2. 确保使用稳定的网络环境
3. 第二次识别会更快（连接已建立）

### 两个音频同时播放

确保：
1. 使用耳机（避免回音）
2. 打断功能正常工作
3. 等待时间足够（已设置为 0.3 秒）

## 📊 性能指标

| 环节 | 延迟 | 说明 |
|------|------|------|
| ASR 首次识别 | 2-4秒 | 包含连接初始化 |
| ASR 后续识别 | 1-2秒 | 连接已建立 |
| LLM 首 token | 200-500ms | 流式输出 |
| TTS 首包 | 200-500ms | 实时合成 |
| 总延迟 | 2-5秒 | 端到端 |

## 📄 许可证

MIT License

## 🙏 致谢

- [DashScope](https://dashscope.aliyuncs.com/) - 提供 ASR 和 TTS 服务
- [Mem0](https://mem0.ai/) - 提供长期记忆管理
- [OpenAI](https://openai.com/) - 提供 LLM API 标准

## 📮 联系方式

如有问题或建议，请提交 Issue。
