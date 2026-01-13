# 更新日志

## 新增功能

### 1. 语音识别模块（ASR）

**新增文件**：
- `src/asr/dashscope_asr.py` - DashScope ASR 客户端
- `src/asr/audio_input.py` - 麦克风音频输入
- `src/asr/interrupt_controller.py` - 语音打断控制器

**功能**：
- ✅ 实时语音识别（使用阿里云 DashScope Paraformer）
- ✅ 麦克风音频输入（16kHz PCM）
- ✅ 语音打断控制（Barge-in）

### 2. 长期记忆模块（Mem0）

**新增文件**：
- `src/memory/mem0_manager.py` - Mem0 记忆管理器

**功能**：
- ✅ 自动提取和存储重要信息
- ✅ 基于上下文检索相关记忆
- ✅ 支持多用户记忆隔离
- ✅ 与 LLM 对话集成

### 3. 语音对话模式

**新增文件**：
- `voice_to_voice.py` - 语音对话模式入口

**功能**：
- ✅ 全语音交互（你说话，AI 说话）
- ✅ 语音打断（说话时自动停止 AI 播放）
- ✅ 实时流式处理（ASR + LLM + TTS）
- ✅ 多线程并行处理（ASR 和 TTS 不阻塞）

### 4. 文字对话模式

**新增文件**：
- `text_to_speech.py` - 文字对话模式入口

**功能**：
- ✅ 文字输入，语音输出
- ✅ 支持所有原有命令（/quit, /role, /clear 等）
- ✅ 实时流式 TTS

## 改进功能

### 1. 打断机制

**改进**：
- ✅ LLM 流式输出可以被打断
- ✅ TTS 播放可以被打断
- ✅ 被打断的对话不保存到历史
- ✅ 节省 API 调用成本

**实现位置**：
- `src/realtime_pipeline.py` - 添加 `stop_event` 检查
- `src/audio/pyaudio_player.py` - 添加 `is_playing` 检查
- `voice_to_voice.py` - 实现打断逻辑

### 2. 音频播放优化

**改进**：
- ✅ 播放器支持立即停止
- ✅ 减少打断后的等待时间（1秒 → 0.3秒）
- ✅ 修复双音频播放问题

**修改文件**：
- `src/audio/pyaudio_player.py` - 优化停止逻辑

### 3. 多线程处理

**改进**：
- ✅ ASR 在独立线程持续监听
- ✅ TTS 在独立线程处理，不阻塞 ASR
- ✅ 支持边说话边识别

**实现位置**：
- `voice_to_voice.py` - 使用 `threading.Thread`

## 删除内容

### 删除的文档
- `ASR_INTEGRATION.md` - 临时文档
- `ASR_QUICKSTART.md` - 临时文档
- `ASR_README.md` - 临时文档
- `INTERRUPT_EXPLANATION.md` - 临时文档
- `AGENT_DESIGN.md` - 临时文档
- `PROMPT_STRUCTURE.md` - 临时文档
- `VOICE_ASSISTANT_PROMPT.md` - 临时文档
- `使用说明.md` - 旧文档

### 删除的测试文件
- `add_test_memory.py`
- `check_all_users.py`
- `check_memories.py`
- `test_asr.py`
- `test_mem0_directly.py`
- `test_mem0_integration.py`
- `test_memory_persistence.py`

## 文件重命名

- `voice_interactive.py` → `voice_to_voice.py` - 更清晰的命名

## 配置变更

### 新增环境变量

```bash
# ASR 配置（使用 QWEN3_API_KEY）
# 无需额外配置，复用 TTS 的 API Key

# Mem0 配置
ENABLE_MEM0=true
MEM0_LLM_API_KEY=sk-xxx
MEM0_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MEM0_LLM_MODEL=qwen-turbo
MEM0_USER_ID=your_user_id
```

## 依赖变更

### 新增依赖

```
pyaudio>=0.2.11        # 音频输入/输出
mem0ai>=0.0.1          # 长期记忆管理
```

### 已有依赖（无变化）

```
dashscope>=1.14.0      # ASR + TTS
openai>=1.0.0          # LLM
python-dotenv>=1.0.0   # 环境变量
requests>=2.31.0       # HTTP 请求
```

## 使用方式变更

### 之前

```bash
python src/main.py
```

### 现在

**模式 1: 文字对话**
```bash
python text_to_speech.py
```

**模式 2: 语音对话**
```bash
python voice_to_voice.py
```

## 技术架构变更

### 之前
```
用户输入（文字） → LLM → TTS → 播放
```

### 现在

**文字对话模式**：
```
用户输入（文字） → LLM → TTS → 播放
                    ↓
                  Mem0 记忆
```

**语音对话模式**：
```
麦克风 → ASR → LLM → TTS → 播放
  ↓              ↓
持续监听      Mem0 记忆
  ↓
打断检测 → 停止 LLM + TTS
```

## 性能改进

| 指标 | 之前 | 现在 | 改进 |
|------|------|------|------|
| 打断响应 | 不支持 | 0.3秒 | ✅ 新增 |
| 多线程 | 单线程 | 多线程 | ✅ 不阻塞 |
| 记忆功能 | 无 | Mem0 | ✅ 新增 |
| 语音输入 | 无 | ASR | ✅ 新增 |

## 已知问题

1. **ASR 首次识别延迟较高**（2-4秒）
   - 原因：包含连接初始化时间
   - 后续识别会更快（1-2秒）

2. **需要麦克风权限**
   - macOS 需要在系统设置中授权

3. **建议使用耳机**
   - 避免外放声音被麦克风录入（回音）

## 下一步计划

- [ ] 优化 ASR 延迟（目标 <1秒）
- [ ] 添加 VAD 参数调优
- [ ] 支持更多 TTS 提供商
- [ ] 添加语音唤醒词
- [ ] 支持多语言识别

## 贡献者

感谢所有贡献者的努力！

---

**版本**: v2.0.0
**日期**: 2025-01-13
**主要变更**: 新增语音识别和长期记忆功能
