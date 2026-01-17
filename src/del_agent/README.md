# AI Data Factory - 轻量级AI数据工厂框架

一个专为处理海量非结构化文本数据而设计的轻量级、高扩展性AI数据工厂框架。

## 🎯 核心特性

- **轻量级架构**：不使用庞大框架，保持对逻辑的完全控制
- **模块化设计**：LLM适配层、提示词管理、智能体基类分离
- **多模型支持**：支持OpenAI、DeepSeek、Moonshot等兼容API
- **结构化输出**：强制JSON格式，使用Pydantic进行数据验证
- **提示词模板**：支持YAML/JSON模板，Jinja2变量替换
- **高扩展性**：为后续多智能体协作和Prompt工程实验提供沙盒环境

## 🏗️ 项目结构

```
src/del_agent/
├── core/                    # 核心模块
│   ├── llm_adapter.py      # LLM适配器层
│   ├── prompt_manager.py   # 提示词管理器
│   └── base_agent.py       # 智能体基类
├── agents/                  # 智能体实现
│   └── raw_comment_cleaner.py  # 评论清洗智能体
├── prompts/                 # 提示词模板
│   └── templates/
│       └── comment_cleaner.yaml  # 评论清洗模板
├── models/                  # 数据模型
│   └── schemas.py          # Pydantic数据模型
├── utils/                   # 工具模块
│   └── config.py           # 配置管理
├── config/                  # 配置文件
│   └── settings.yaml       # 主配置文件
└── examples/                # 示例代码
    └── demo.py             # 演示脚本
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd AI-Sandbox

# 安装依赖
pip install -r requirements.txt

# 设置API密钥
cp .env.example .env
# 编辑 .env 文件，设置你的API密钥
```

### 2. 基本使用

```python
import os
from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.agents.raw_comment_cleaner import RawCommentCleaner

# 创建LLM提供者
llm_provider = OpenAICompatibleProvider(
    model_name="gpt-3.5-turbo",
    api_key=os.getenv('OPENAI_API_KEY')
)

# 创建评论清洗智能体
agent = RawCommentCleaner(llm_provider=llm_provider)

# 处理单条评论
result = agent.process("这老板简直是'学术妲己'，太会画饼了！经费倒是多，但不发给我们。")

print(f"事实内容: {result.factual_content}")
print(f"情绪强度: {result.emotional_intensity}")
print(f"关键词: {result.keywords}")
```

### 3. 批量处理

```python
# 批量处理评论
comments = [
    "实验室氛围还行，师兄师姐都挺友好的。",
    "这个课题组简直是地狱！天天加班到深夜！",
    "导师人很好，指导很耐心，就是项目进度有点慢。"
]

results = agent.analyze_batch(comments)

# 获取统计汇总
summary = agent.get_processing_summary(results)
print(f"成功率: {summary['success_rate']:.1%}")
print(f"平均情绪强度: {summary['avg_emotional_intensity']:.2f}")
```

## 🔧 配置说明

### LLM提供者配置

在 `config/settings.yaml` 中配置不同的LLM提供者：

```yaml
llm_providers:
  openai:
    provider: "openai"
    model_name: "gpt-3.5-turbo"
    api_key: ""  # 从环境变量获取
    temperature: 0.7
    
  deepseek:
    provider: "deepseek"
    model_name: "deepseek-chat"
    api_key: ""  # 从环境变量获取
    base_url: "https://api.deepseek.com"
```

### 智能体配置

```yaml
agents:
  comment_cleaner:
    name: "comment_cleaner"
    description: "原始评论清洗智能体"
    llm_provider: "openai"
    prompt_template: "comment_cleaner"
    max_retries: 3
```

## 📝 提示词模板

提示词模板使用YAML格式，支持Jinja2变量替换：

```yaml
name: comment_cleaner
system_prompt: |
  你是一个专业的文本分析专家，专门用于处理中文网络评论...
  
user_prompt: |
  请分析以下原始评论：
  "{{ raw_comment }}"
  
  评论长度：{{ comment_length }} 字符
```

## 🎨 扩展开发

### 创建新的智能体

1. 继承 `BaseAgent` 基类
2. 实现 `get_output_schema()` 和 `get_prompt_template_name()` 方法
3. 创建对应的Pydantic数据模型
4. 编写提示词模板

### 示例：创建新的智能体

```python
from del_agent.core.base_agent import BaseAgent
from pydantic import BaseModel

class MyCustomResult(BaseModel):
    result: str
    confidence: float

class MyCustomAgent(BaseAgent):
    def get_output_schema(self):
        return MyCustomResult
    
    def get_prompt_template_name(self):
        return "my_custom_template"
```

## 🔍 监控和调试

框架内置了详细的日志记录和统计功能：

```python
# 获取智能体统计信息
stats = agent.get_stats()
print(f"执行次数: {stats['execution_count']}")
print(f"平均执行时间: {stats['average_execution_time']}")

# 处理结果包含详细的元数据
result = agent.process("测试评论")
print(f"执行时间: {result.execution_time}")
print(f"时间戳: {result.timestamp}")
print(f"元数据: {result.metadata}")
```

## 🛠️ 环境要求

- Python 3.8+
- 支持的LLM API密钥（OpenAI、DeepSeek、Moonshot等）

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！