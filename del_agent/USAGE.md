# DEL Agent - 使用指南

## 快速开始

### 1. 安装依赖

```bash
# 基础依赖（必需）
pip install -r requirements.txt

# 语音模式额外依赖（可选）
pip install pyaudio websockets
```

### 2. 配置

#### 配置文件
复制配置模板并编辑：
```bash
cp del_agent/config/settings.yaml.example del_agent/config/settings.yaml
```

#### 环境变量
创建 `.env` 文件（用于语音模式）：
```bash
# API 密钥
ARK_API_KEY=your_api_key_here
APPID=your_app_id
RESOURCE_ID=your_resource_id

# VikingDB（可选）
VIKINGDB_API_KEY=your_vikingdb_key
VIKINGDB_HOST=your_vikingdb_host
VIKINGDB_REGION=your_region
VIKINGDB_SCHEMA=your_schema
```

### 3. 运行

#### 文本交互模式
```bash
python del_agent/main.py --mode text
```

示例对话：
```
用户：你好！
助手：你好！有什么我可以帮助你的吗？

用户：今天天气怎么样？
助手：[根据你的个性化设置回复]

用户：退出
助手：再见！
```

#### 语音交互模式（麦克风）
```bash
python del_agent/main.py --mode voice
```

#### 语音交互模式（音频文件）
```bash
python del_agent/main.py --mode voice --audio data/test.wav
```

#### 启用高级功能
```bash
# 启用回声消除
python del_agent/main.py --mode voice --aec

# 启用记忆存储（VikingDB）
python del_agent/main.py --mode voice --memory

# 组合使用
python del_agent/main.py --mode voice --aec --memory
```

## 功能说明

### 文本模式
- ✅ 多轮对话
- ✅ 意图识别（闲聊/查询/提供信息）
- ✅ 个性化回复
- ✅ 用户画像自动更新
- ✅ 信息提取

### 语音模式
- ✅ 实时语音识别
- ✅ 语音合成输出
- ✅ 端到端对话
- ✅ 回声消除（可选）
- ✅ 记忆存储（可选）

## 架构说明

### 整体架构
```
del_agent/
├── main.py                    # 统一入口
├── frontend/
│   ├── orchestrator.py        # 文本模式路由器
│   ├── voice_adapter.py       # 语音模式适配器
│   └── user_profile.py        # 用户画像管理
├── agents/
│   ├── persona.py             # 个性化对话
│   ├── info_extractor.py      # 信息提取
│   ├── critic.py              # 评论审核
│   ├── slang_decoder.py       # 俚语解码
│   ├── weigher.py             # 权重评分
│   └── compressor.py          # 知识压缩
├── backend/
│   └── factory.py             # 后端处理流水线
├── core/
│   ├── base_agent.py          # 智能体基类
│   ├── llm_adapter.py         # LLM 适配器
│   └── verification.py        # 核验循环
└── tests/
    └── test_*.py              # 测试文件
```

### 交互流程

#### 文本模式
```
用户输入
   ↓
FrontendOrchestrator（路由器）
   ↓
意图识别 → PersonaAgent（闲聊）
         → InfoExtractorAgent（信息提取）
         → BackendPipeline（后端处理）
   ↓
个性化回复
```

#### 语音模式
```
语音输入
   ↓
VoiceAdapter
   ↓
doubao_sample（端到端语音对话）
   ↓
语音输出
```

## 测试

### 运行所有测试
```bash
# 运行所有测试
python -m pytest del_agent/tests/ -v

# 运行特定测试
python -m pytest del_agent/tests/test_voice_adapter.py -v
python -m pytest del_agent/tests/test_complete_pipeline.py -v
```

### 测试覆盖率
```bash
python -m pytest --cov=del_agent del_agent/tests/
```

## 开发指南

### 添加新的智能体
1. 继承 `BaseAgent` 类
2. 实现 `process()` 方法
3. 添加到 `backend/factory.py` 流水线
4. 编写测试

示例：
```python
from del_agent.core.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def process(self, input_data, context=None):
        # 实现你的逻辑
        result = self.llm_adapter.generate(...)
        return self.verify(result)
```

### 自定义 LLM 后端
```python
from del_agent.core.llm_adapter import LLMProvider

# 在 settings.yaml 中配置
llm:
  providers:
    my_provider:
      backend: openai  # 或 custom
      api_key: xxx
      model: gpt-4
```

## 常见问题

### Q: pyaudio 安装失败
A: 根据你的系统：
```bash
# macOS
brew install portaudio
pip install pyaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev
pip install pyaudio

# Windows
pip install pipwin
pipwin install pyaudio
```

### Q: 语音模式无法启动
A: 检查：
1. API 密钥是否正确设置
2. doubao_sample 配置是否完整
3. pyaudio 是否正确安装
4. 麦克风/扬声器是否可用

使用环境检查工具：
```python
from del_agent.frontend.voice_adapter import VoiceAdapter

env = VoiceAdapter.check_environment()
print(env)
# {'doubao_sample_exists': True, 'config_valid': True}

config = VoiceAdapter.validate_config()
print(config)
# {'api_key': True, 'appid': True, ...}
```

### Q: 文本模式没有响应
A: 检查：
1. LLM 配置是否正确
2. API 密钥是否有效
3. 网络连接是否正常
4. 查看日志：`--debug` 参数

### Q: 如何切换 LLM 模型
A: 编辑 `del_agent/config/settings.yaml`：
```yaml
llm:
  providers:
    default:
      model: gpt-4  # 或其他模型
```

## 性能优化

### 建议
1. **文本模式**：使用较小的模型（如 gpt-3.5-turbo）以降低延迟
2. **语音模式**：启用回声消除（`--aec`）提高质量
3. **记忆存储**：仅在需要长期记忆时启用（`--memory`）
4. **并发控制**：在 settings.yaml 中设置 `max_concurrent_requests`

### 典型配置
```yaml
# 快速响应
llm:
  default:
    model: gpt-3.5-turbo
    temperature: 0.7
    max_tokens: 500

# 高质量回复
llm:
  default:
    model: gpt-4
    temperature: 0.9
    max_tokens: 2000
```

## 更多信息

- 📖 [完整文档](docs/)
- 🏗️ [架构说明](del_agent/ARCHITECTURE.md)
- 📊 [性能分析](del_agent/docs/PERFORMANCE_TIMING.md)
- 🧪 [测试报告](del_agent/config/project1/result_report/)
- 📋 [项目规划](del_agent/config/project1/del2.md)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[添加许可证信息]

---

**版本**：1.0.0  
**最后更新**：2025-01-19
