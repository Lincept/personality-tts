# AI Data Factory - AI导师评价交互网络

一个基于多智能体架构的AI导师评价处理与交互平台，将非结构化评论转化为结构化知识节点。

## 🎯 核心特性

- **模块化智能体架构**：基于 `BaseAgent` 的统一接口，易于扩展
- **核验循环机制**：通过 `CriticAgent` 实现质量控制
- **多模型支持**：支持 OpenAI、DeepSeek、Moonshot、豆包等多种 LLM
- **完整数据流水线**：从原始评论到结构化知识节点的端到端处理
- **动态黑话词典**：支持 JSON 和 Mem0 两种存储方式
- **权重评估算法**：基于身份可信度、时间衰减、离群点检测
- **结构化输出**：强制 JSON 格式，使用 Pydantic 进行数据验证

## 📊 当前版本状态

**版本**: v2.3.0  
**更新日期**: 2026年1月19日

### ✅ 已完成的功能

#### Phase 1: 核心基础设施
- ✅ 核验循环机制（VerificationLoop）
- ✅ 扩展数据模型（6个核心模型）
- ✅ BaseAgent 增强（支持核验循环）

#### Phase 2: 后端数据工厂
- ✅ **RawCommentCleaner**（评论清洗智能体）
- ✅ **CriticAgent**（判别节点智能体）
- ✅ **SlangDecoderAgent**（黑话解码智能体）
- ✅ **WeigherAgent**（权重分析智能体）✨ 新增
- ✅ **CompressorAgent**（结构化压缩智能体）✨ 新增
- ✅ **DataFactoryPipeline**（流水线控制器）✨ 新增

### 🔄 下一步计划

#### Phase 3: 前端交互层（规划中）
- [ ] UserProfileManager（用户画像管理器）
- [ ] PersonaAgent（人设交互智能体）
- [ ] InfoExtractorAgent（信息抽取器）
- [ ] FrontendOrchestrator（前端编排器）

#### Phase 4: 系统整合（规划中）
- [ ] VectorDatabase 接口
- [ ] KnowledgeGraph 接口
- [ ] DimensionLinker（多维串联器）
- [ ] 完整系统演示

## 🏗️ 项目结构

```
del_agent/
├── core/                    # 核心模块
│   ├── llm_adapter.py      # LLM适配器层
│   ├── prompt_manager.py   # 提示词管理器
│   ├── base_agent.py       # 智能体基类
│   ├── verification.py     # 核验循环机制
│   └── dictionary_store.py # 词典存储框架
├── agents/                  # 智能体实现
│   ├── raw_comment_cleaner.py      # 评论清洗智能体
│   ├── critic.py                   # 判别节点智能体
│   ├── slang_decoder.py            # 黑话解码智能体
│   ├── weigher.py                  # 权重分析智能体 ✨
│   ├── compressor.py               # 结构化压缩智能体 ✨
│   └── strictness_prompt_generator.py  # 严格度提示词生成器
├── backend/                 # 后端数据工厂 ✨
│   └── factory.py          # 流水线控制器
├── prompts/                 # 提示词模板
│   └── templates/
│       ├── comment_cleaner.yaml
│       ├── critic.yaml
│       ├── slang_decoder.yaml
│       └── strictness_prompt_generator.yaml
├── models/                  # 数据模型
│   └── schemas.py          # Pydantic数据模型（7个核心模型）
├── utils/                   # 工具模块
│   └── config.py           # 配置管理
├── config/                  # 配置文件
│   ├── settings.yaml       # 主配置文件
│   └── project1/           # 项目文档
│       ├── req1.md         # 需求文档
│       ├── del1.md         # 交付计划
│       └── result_report/  # 执行报告
├── tests/                   # 测试文件
│   ├── test_pipeline.py    # 流水线测试 ✨
│   ├── test_critic.py      # 判别器测试
│   └── test_verification.py # 核验循环测试
├── examples/                # 示例代码
│   └── demo.py             # 演示脚本
├── ARCHITECTURE.md          # 系统架构文档 ✨
└── README.md               # 本文件
```

📖 **详细架构说明**: 请参阅 [ARCHITECTURE.md](ARCHITECTURE.md)

## 🚀 快速开始

### 1. 环境准备

```bash
# 进入 del_agent 项目目录
cd del_agent

# 安装依赖
pip install -r ../requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 文件，根据使用的 LLM 提供者填写对应的 API 密钥
```

**注意**：.env 文件不会被提交到 git 仓库，保护你的密钥安全。

### 2. 运行示例

```bash
# 方式一：使用快速启动脚本（推荐）
cd del_agent
./run.sh test-config  # 测试配置
./run.sh demo        # 运行完整演示

# 方式二：测试数据工厂流水线 ✨
python tests/test_pipeline.py

# 方式三：测试各个智能体
python tests/test_critic.py
python tests/test_slang_decoder.py
python tests/test_verification.py

# 方式四：直接运行（需要设置 PYTHONPATH）
cd /path/to/AI-Sandbox
PYTHONPATH=$(pwd):$PYTHONPATH python del_agent/examples/demo.py
```

### 3. 基本使用

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

### 3. 使用数据工厂流水线 ✨ **新增**

```python
from core.llm_adapter import LLMProvider
from backend.factory import DataFactoryPipeline
from models.schemas import RawReview
from utils.config import ConfigManager
from datetime import datetime

# 加载配置
config = ConfigManager()
llm_config = config.get_llm_config("deepseek")

# 创建 LLM 提供者
llm_provider = LLMProvider(llm_config)

# 创建数据工厂流水线（可选启用核验循环）
pipeline = DataFactoryPipeline(
    llm_provider=llm_provider,
    enable_verification=False  # 是否启用核验循环
)

# 创建原始评论
review = RawReview(
    content="这个老板简直是'学术妲己'，天天画饼！说好的经费充足，结果学生津贴发得少得可怜。",
    source_metadata={
        "platform": "知乎",
        "verified": True,
        "identity": "student",
        "mentor_name": "Zhang San"
    },
    timestamp=datetime.now()
)

# 处理评论，生成结构化知识节点
knowledge_node = pipeline.process_raw_review(review)

print(f"导师ID: {knowledge_node.mentor_id}")
print(f"评价维度: {knowledge_node.dimension}")
print(f"事实内容: {knowledge_node.fact_content}")
print(f"权重评分: {knowledge_node.weight_score:.2f}")
print(f"标签: {', '.join(knowledge_node.tags)}")

# 查看统计信息
stats = pipeline.get_statistics()
print(f"成功率: {stats['success_rate']:.1%}")
```

### 4. 批量处理

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

### 环境变量配置

项目使用 `.env` 文件管理敏感信息（API 密钥）：

1. 复制模板文件：`cp .env.example .env`
2. 根据使用的 LLM 提供者，在 `.env` 中填写相应的 API 密钥：

```bash
# 豆包（默认）
DOBAO_API_KEY=your_dobao_api_key_here
DOBAO_API_SECRET=your_dobao_api_secret_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 其他提供者...
```

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