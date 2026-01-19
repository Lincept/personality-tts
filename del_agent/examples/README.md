# DEL Agent 示例程序

本目录包含 DEL Agent 的示例程序，帮助你快速了解和使用系统的各项功能。

## 📁 目录结构

```
examples/
├── README.md              # 本文件
├── example_text.py        # 文本交互示例
└── example_voice.py       # 语音交互示例
```

## 🚀 快速开始

### 1. 环境准备

确保已安装所有依赖：

```bash
cd del_agent
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并配置环境变量文件：

```bash
cp env.example .env
# 编辑 .env 文件，填写必要的配置信息
```

必要的环境变量：
- `VOLCENGINE_APP_ID`: 火山引擎应用ID（语音模式需要）
- `VOLCENGINE_TOKEN`: 火山引擎访问令牌（语音模式需要）
- `VOLCENGINE_CLUSTER_ID`: 火山引擎集群ID（语音模式需要）

## 📝 示例说明

### 文本交互示例 (example_text.py)

演示如何使用 FrontendOrchestrator 进行文本对话。

**功能展示：**
- ✓ 创建和配置 Orchestrator
- ✓ 单次对话处理
- ✓ 多轮对话维护
- ✓ 查看对话历史
- ✓ 用户画像管理
- ✓ 清空对话记录

**运行方式：**

```bash
# 方式1：直接运行
python examples/example_text.py

# 方式2：通过主程序运行
python main.py --mode text
```

**示例输出：**

```
====================================================
DEL Agent 文本交互示例
====================================================

📝 Step 1: 初始化 LLM Provider...
   ✓ LLM Provider 初始化成功

📝 Step 2: 创建 FrontendOrchestrator...
   ✓ Orchestrator 创建成功

📝 Step 3: 单次对话示例
------------------------------------------------------------
用户: 你好，今天天气不错
助手: 你好！我是 DEL Agent。很高兴为你服务！

[调试] 意图: chat, 执行时间: 0.15s
```

### 语音交互示例 (example_voice.py)

演示如何使用 VoiceAdapter 进行语音对话。

**功能展示：**
- ✓ 检查音频环境
- ✓ 实时语音对话
- ✓ 音频文件处理
- ✓ 文本模拟测试

**运行方式：**

```bash
# 快速测试（不需要音频设备）
python examples/example_voice.py --quick

# 完整交互（需要音频设备）
python examples/example_voice.py

# 通过主程序运行（实时语音）
python main.py --mode audio
```

**交互模式：**

1. **实时语音对话**：需要麦克风和扬声器
2. **音频文件测试**：处理预录制的音频文件
3. **文本模拟测试**：使用文本模拟语音交互（推荐首次测试）

**环境要求：**

实时语音模式需要安装 PyAudio：

```bash
# Ubuntu/Debian
sudo apt-get install python3-pyaudio

# macOS
brew install portaudio
pip install pyaudio

# Windows
pip install pyaudio
```

## 🧪 测试流程

### 初次使用建议流程

1. **测试文本交互**（最简单）
   ```bash
   python examples/example_text.py
   ```

2. **快速测试语音适配器**（无需音频设备）
   ```bash
   python examples/example_voice.py --quick
   ```

3. **文本模拟语音**（无需音频设备）
   ```bash
   python examples/example_voice.py
   # 然后选择模式 3
   ```

4. **实时语音对话**（需要音频设备和配置）
   ```bash
   python examples/example_voice.py
   # 然后选择模式 1
   ```

## 🎯 使用场景

### 场景1：快速体验系统功能

```bash
# 使用 Mock LLM，无需配置
python examples/example_text.py
```

适合：快速了解系统结构和基本流程

### 场景2：本地开发测试

```bash
# 配置真实的 LLM Provider
# 编辑 del_agent/config/settings.yaml
python examples/example_text.py
```

适合：开发新功能时的快速测试

### 场景3：端到端语音测试

```bash
# 配置火山引擎语音服务
# 编辑 .env 文件
python examples/example_voice.py
```

适合：测试完整的语音交互流程

## 📊 性能指标

运行示例时会显示以下性能指标：

- **执行时间**：单次请求的处理时间
- **意图识别**：识别出的用户意图类型（chat/query/provide_info）
- **对话轮数**：当前会话的对话轮数
- **用户画像**：用户的个性化参数（幽默度、正式度、细节偏好）

## 🔧 故障排除

### 问题1：LLM Provider 初始化失败

**原因**：配置文件缺失或配置错误

**解决**：
1. 检查 `del_agent/config/settings.yaml` 是否存在
2. 确认 LLM 配置参数是否正确
3. 可以使用示例中的 Mock LLM 进行测试

### 问题2：PyAudio 不可用

**原因**：未安装 PyAudio 或系统缺少依赖

**解决**：
```bash
# 查看详细错误
python -c "import pyaudio"

# 根据系统安装
# Ubuntu: sudo apt-get install portaudio19-dev python3-pyaudio
# macOS: brew install portaudio && pip install pyaudio
# Windows: pip install pyaudio
```

### 问题3：语音服务连接失败

**原因**：环境变量未配置或配置错误

**解决**：
1. 检查 `.env` 文件是否存在
2. 确认火山引擎配置是否正确
3. 运行 `source .env` 加载环境变量

### 问题4：Import Error

**原因**：项目路径未正确添加

**解决**：
```bash
# 确保从项目根目录运行
cd /path/to/AI-Sandbox
python del_agent/examples/example_text.py

# 或设置 PYTHONPATH
export PYTHONPATH=/path/to/AI-Sandbox:$PYTHONPATH
```

## 📚 进阶使用

### 自定义 LLM Provider

在示例中修改 LLM 创建部分：

```python
from del_agent.core.llm_adapter import LLMProvider

# 使用自定义配置
llm_provider = LLMProvider(
    provider="your_provider",
    api_key="your_api_key",
    model="your_model"
)
```

### 启用 RAG 检索

```python
orchestrator = FrontendOrchestrator(
    llm_provider=llm_provider,
    enable_rag=True  # 启用 RAG
)
```

### 自定义用户画像

```python
from del_agent.models.schemas import UserPersonalityVector

# 设置用户个性化参数
profile = orchestrator.profile_manager.get_profile(user_id)
profile.personality_vector = UserPersonalityVector(
    humor_level=0.8,      # 幽默度
    formality_level=0.3,  # 正式度
    detail_preference=0.7 # 细节偏好
)
orchestrator.profile_manager.save_profile(profile)
```

## 🤝 贡献

欢迎提交新的示例程序！请确保：

1. 代码清晰，注释完整
2. 包含使用说明
3. 处理常见错误情况
4. 提供示例输出

## 📄 许可

本项目遵循 MIT 许可证。

## 📮 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

---

**版本**：1.0.0  
**更新日期**：2026-01-19
