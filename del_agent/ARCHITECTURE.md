# AI导师评价交互网络 - 系统架构文档

**版本**: v2.3.0  
**更新日期**: 2026年1月19日  
**状态**: Phase 2 后端数据工厂已完成

---

## 1. 系统概览

本系统是一个基于多智能体架构的AI导师评价处理与交互平台，采用**双层设计**：
- **后端数据工厂**：将非结构化评论转化为结构化知识节点
- **前端交互层**（规划中）：基于用户画像的个性化交互

### 1.1 核心特性

- ✅ **模块化智能体架构**：基于 `BaseAgent` 的统一接口
- ✅ **核验循环机制**：通过 `CriticAgent` 实现质量控制
- ✅ **多模型支持**：统一的 LLM 接口（OpenAI、DeepSeek、Moonshot等）
- ✅ **动态黑话词典**：支持 JSON 和 Mem0 两种存储方式
- ✅ **权重评估算法**：基于身份可信度、时间衰减、离群点检测
- ✅ **流水线编排**：自动化的端到端处理流程

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端交互层 (规划中)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ UserProfile  │  │ PersonaAgent │  │ InfoExtractor│          │
│  │  Manager     │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │ 双向通信
┌────────────────────────────┴────────────────────────────────────┐
│                      后端数据工厂 (已完成)                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           DataFactoryPipeline (流水线控制器)              │    │
│  │                                                           │    │
│  │   RawReview → Cleaner → Decoder → Weigher → Compressor  │    │
│  │                  ↓          ↓         ↓          ↓       │    │
│  │              CriticAgent (核验循环，可选)                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  各个智能体详细功能：                                              │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ RawCommentCleaner│  │ SlangDecoderAgent│                     │
│  │ - 去情绪化        │  │ - 识别黑话        │                     │
│  │ - 提取事实        │  │ - 标准翻译        │                     │
│  │ - 提取关键词      │  │ - 动态词典        │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  WeigherAgent    │  │ CompressorAgent  │                     │
│  │ - 身份可信度      │  │ - 维度提取        │                     │
│  │ - 时间衰减        │  │ - 内容压缩        │                     │
│  │ - 离群点检测      │  │ - 生成知识节点    │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                   │
│  ┌──────────────────────────────────────┐                        │
│  │         CriticAgent (判别节点)         │                        │
│  │  - 质量评估                           │                        │
│  │  - 反馈生成                           │                        │
│  │  - 严格度控制 (5级)                   │                        │
│  │  - 支持动态提示词生成                  │                        │
│  └──────────────────────────────────────┘                        │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                        核心基础设施                              │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │   BaseAgent    │  │ LLMProvider    │  │ PromptManager   │ │
│  │  (抽象基类)     │  │ (多模型支持)    │  │ (模板管理)       │ │
│  └────────────────┘  └────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │VerificationLoop│  │DictionaryStore │  │  Pydantic       │ │
│  │  (核验循环)     │  │ (词典存储)      │  │  (数据模型)      │ │
│  └────────────────┘  └────────────────┘  └─────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. 核心组件说明

### 3.1 核心层 (Core Layer)

#### 3.1.1 BaseAgent
**文件**: [core/base_agent.py](core/base_agent.py)

**功能**：
- 所有智能体的抽象基类
- 定义统一的处理流程：`prepare_input → render_prompt → LLM.generate → validate_output`
- 支持核验循环：`process_with_verification()` 方法

**关键方法**：
```python
def process(raw_input, **kwargs) -> BaseModel
def process_with_verification(raw_input, critic_agent, max_retries, **kwargs) -> BaseModel
def get_prompt_template_name() -> str
def get_output_schema() -> Type[BaseModel]
```

#### 3.1.2 VerificationLoop
**文件**: [core/verification.py](core/verification.py)

**功能**：
- 实现 `Agent Output → Critic Check → Pass/Retry` 循环
- 支持自适应重试（根据历史成功率调整）
- 记录反馈历史和统计信息

**核心逻辑**：
```python
for attempt in range(max_retries):
    output = generator_func()
    feedback = critic_func(output, context)
    if feedback.is_approved:
        return output, feedback_history
```

#### 3.1.3 LLMProvider
**文件**: [core/llm_adapter.py](core/llm_adapter.py)

**功能**：
- 统一的多模型接口
- 支持提供商：OpenAI、DeepSeek、Moonshot、豆包等
- 结构化输出（基于 Pydantic）
- 自动重试机制

#### 3.1.4 PromptManager
**文件**: [core/prompt_manager.py](core/prompt_manager.py)

**功能**：
- 从 YAML/JSON 加载提示词模板
- Jinja2 模板引擎支持
- 缓存和预编译

#### 3.1.5 DictionaryStore
**文件**: [core/dictionary_store.py](core/dictionary_store.py)

**功能**：
- 黑话词典存储抽象接口
- 实现类：`JSONDictionaryStore`、`Mem0DictionaryStore`
- 支持增删改查和语义检索

---

### 3.2 智能体层 (Agent Layer)

#### 3.2.1 RawCommentCleaner（清洗智能体）
**文件**: [agents/raw_comment_cleaner.py](agents/raw_comment_cleaner.py)

**功能**：
- 去除情绪化表达
- 提取事实内容
- 评估情绪强度
- 提取关键词

**输出模型**: `CommentCleaningResult`

#### 3.2.2 SlangDecoderAgent（黑话解码智能体）
**文件**: [agents/slang_decoder.py](agents/slang_decoder.py)

**功能**：
- 识别网络黑话、学术术语
- 翻译为标准表述
- 维护动态黑话词典（JSON/Mem0）
- 支持批量解码

**输出模型**: `SlangDecodingResult`

**示例黑话**：
- "学术妲己" → "善于承诺但不兑现的导师"
- "画饼" → "做出承诺但不实现"

#### 3.2.3 CriticAgent（判别节点智能体）
**文件**: [agents/critic.py](agents/critic.py)

**功能**：
- 评估其他 Agent 输出质量
- 生成结构化反馈 (`CriticFeedback`)
- 5级严格度控制（0.0-1.0）
- 支持静态和动态提示词

**评估维度**（总分100）：
1. 事实准确性（40分）
2. 信息完整性（30分）
3. 格式正确性（20分）
4. 一致性（10分）

**输出模型**: `CriticFeedback`

#### 3.2.4 StrictnessPromptGenerator（严格度提示词生成器）
**文件**: [agents/strictness_prompt_generator.py](agents/strictness_prompt_generator.py)

**功能**：
- 根据严格度参数动态生成 Critic 提示词
- 支持 5 种严格度等级
- 与 CriticAgent 配合使用

#### 3.2.5 WeigherAgent（权重分析智能体）✨ **新增**
**文件**: [agents/weigher.py](agents/weigher.py)

**功能**：
- 计算信息可信度评分
- 基于三个维度：
  - **身份可信度** (50%)：实名认证、身份验证、账号活跃度
  - **时间衰减** (30%)：使用指数衰减模型（半衰期180天）
  - **离群点检测** (20%惩罚)：极端情绪、异常长度

**权重公式**：
```python
base_score = identity_confidence * 0.5 + time_decay * 0.3
outlier_penalty = 0.2 if outlier_status else 0
final_score = max(0, min(1, base_score - outlier_penalty))
```

**输出模型**: `WeightAnalysisResult`

#### 3.2.6 CompressorAgent（结构化压缩智能体）✨ **新增**
**文件**: [agents/compressor.py](agents/compressor.py)

**功能**：
- 将处理后的信息映射到 `StructuredKnowledgeNode`
- 提取评价维度（9种维度）
- 压缩冗余信息，保留核心内容

**支持的维度**：
- `Funding`（经费）
- `Personality`（性格）
- `Academic_Geng`（学术梗）
- `Work_Pressure`（工作压力）
- `Lab_Atmosphere`（实验室氛围）
- `Publication`（发表）
- `Career_Development`（职业发展）
- `Equipment`（设备）
- `Other`（其他）

**输出模型**: `CompressionResult`

---

### 3.3 流水线层 (Pipeline Layer)

#### 3.3.1 DataFactoryPipeline（数据工厂流水线）✨ **新增**
**文件**: [backend/factory.py](backend/factory.py)

**功能**：
- 编排所有后端智能体的执行顺序
- 管理核验循环（可选）
- 统计处理信息
- 支持批量处理

**处理流程**：
```
RawReview 
  ↓
CleanerAgent (可选核验)
  ↓ factual_content
SlangDecoderAgent
  ↓ decoded_text
WeigherAgent
  ↓ weight_score
CompressorAgent
  ↓
StructuredKnowledgeNode
```

**关键方法**：
```python
def process_raw_review(raw_review: RawReview) -> StructuredKnowledgeNode
def process_batch(raw_reviews: List[RawReview]) -> List[StructuredKnowledgeNode]
def get_statistics() -> Dict[str, Any]
```

---

### 3.4 数据模型层 (Data Model Layer)

**文件**: [models/schemas.py](models/schemas.py)

#### 核心数据模型：

1. **RawReview**（原始评价数据）
   ```python
   content: str
   source_metadata: Dict[str, Any]
   timestamp: datetime
   ```

2. **CriticFeedback**（判别反馈）
   ```python
   is_approved: bool
   reasoning: str
   suggestion: str
   confidence_score: float
   ```

3. **StructuredKnowledgeNode**（结构化知识节点）
   ```python
   mentor_id: str
   dimension: str
   fact_content: str
   original_nuance: str
   weight_score: float
   tags: List[str]
   last_updated: datetime
   ```

4. **SlangDecodingResult**（黑话解码结果）
5. **WeightAnalysisResult**（权重分析结果）✨ **新增**
6. **CompressionResult**（压缩结果）✨ **新增**
7. **CommentCleaningResult**（评论清洗结果）

---

## 4. 数据流示例

### 4.1 单条评论处理流程

**输入**：
```python
RawReview(
    content="这个老板简直是'学术妲己'，天天画饼！说好的经费充足，结果学生津贴发得少得可怜。",
    source_metadata={
        "platform": "知乎",
        "verified": True,
        "identity": "student",
        "mentor_name": "Zhang San"
    }
)
```

**Step 1 - CleanerAgent**：
```python
CommentCleaningResult(
    factual_content="经费充足，但学生津贴发放较少",
    emotional_intensity=0.8,
    keywords=["经费", "津贴", "学术妲己"]
)
```

**Step 2 - SlangDecoderAgent**：
```python
SlangDecodingResult(
    decoded_text="导师善于承诺但不兑现，经费充足但学生津贴发放较少",
    slang_dictionary={"学术妲己": "善于承诺但不兑现的导师", "画饼": "..."}
)
```

**Step 3 - WeigherAgent**：
```python
WeightAnalysisResult(
    weight_score=0.78,
    identity_confidence=0.85,
    time_decay=0.95,
    outlier_status=False
)
```

**Step 4 - CompressorAgent**：
```python
CompressionResult(
    structured_node=StructuredKnowledgeNode(
        mentor_id="mentor_zhang_san",
        dimension="Funding",
        fact_content="经费充足，但学生津贴发放较少",
        weight_score=0.78,
        tags=["经费", "津贴"]
    )
)
```

---

## 5. 配置管理

### 5.1 配置文件结构

```
config/
├── settings.yaml          # 主配置文件
├── project1/              # 项目配置
│   ├── req1.md           # 需求文档
│   ├── del1.md           # 交付计划
│   └── result_report/    # 执行报告
prompts/
└── templates/             # 提示词模板
    ├── comment_cleaner.yaml
    ├── slang_decoder.yaml
    ├── critic.yaml
    └── strictness_prompt_generator.yaml
```

### 5.2 环境变量

在 `.env` 文件中配置：
```bash
# DeepSeek
DEEPSEEK_API_KEY=sk-xxx

# OpenAI
OPENAI_API_KEY=sk-xxx

# Moonshot
MOONSHOT_API_KEY=sk-xxx

# 豆包 (Doubao)
DOUBAO_API_KEY=xxx
DOUBAO_API_SECRET=xxx
```

---

## 6. 使用示例

### 6.1 基本使用

```python
from core.llm_adapter import LLMProvider
from backend.factory import DataFactoryPipeline
from models.schemas import RawReview
from utils.config import ConfigManager

# 加载配置
config = ConfigManager()
llm_config = config.get_llm_config("deepseek")

# 创建 LLM 提供者
llm_provider = LLMProvider(llm_config)

# 创建流水线（不启用核验）
pipeline = DataFactoryPipeline(
    llm_provider=llm_provider,
    enable_verification=False
)

# 处理单条评论
review = RawReview(
    content="导师人很好，但实验室设备老旧...",
    source_metadata={"platform": "知乎", ...}
)

knowledge_node = pipeline.process_raw_review(review)
print(knowledge_node.dimension)  # 输出: "Equipment"
```

### 6.2 启用核验循环

```python
# 创建流水线（启用核验）
pipeline = DataFactoryPipeline(
    llm_provider=llm_provider,
    enable_verification=True,
    max_retries=3,
    strictness_level=0.7
)

knowledge_node = pipeline.process_raw_review(review)
```

### 6.3 批量处理

```python
reviews = [review1, review2, review3]
knowledge_nodes = pipeline.process_batch(reviews)

# 查看统计
stats = pipeline.get_statistics()
print(f"成功率: {stats['success_rate']:.1%}")
```

---

## 7. 测试

### 7.1 运行测试

```bash
# 测试流水线
python tests/test_pipeline.py

# 测试单个智能体
python tests/test_critic.py
python tests/test_slang_decoder.py
python tests/test_verification.py
```

### 7.2 测试覆盖

- ✅ 核验循环机制测试
- ✅ 各个智能体单元测试
- ✅ 流水线集成测试
- ✅ 批量处理测试
- ✅ 核验循环性能测试

---

## 8. 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| 框架 | Pydantic, Jinja2 |
| LLM | OpenAI API, DeepSeek, Moonshot, 豆包 |
| 数据存储 | JSON, Mem0 (向量存储) |
| 日志 | Python logging |
| 配置 | YAML, 环境变量 |

---

## 9. 下一步规划（Phase 3-4）

### Phase 3: 前端交互层（规划中）
- [ ] UserProfileManager（用户画像管理器）
- [ ] PersonaAgent（人设交互智能体）
- [ ] InfoExtractorAgent（信息抽取器）
- [ ] FrontendOrchestrator（前端编排器）

### Phase 4: 系统整合（规划中）
- [ ] 向量数据库接口（VectorDB）
- [ ] 知识图谱接口（KnowledgeGraph）
- [ ] DimensionLinker（多维串联器）
- [ ] 完整闭环演示（main.py）

---

## 10. 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2024年 | 初始版本，基础框架 |
| v2.0 | 2026-01 | Phase 1 完成：核验循环和数据模型 |
| v2.1 | 2026-01 | Phase 2.1 完成：CriticAgent |
| v2.2 | 2026-01 | Phase 2.2 完成：SlangDecoderAgent |
| v2.3 | 2026-01-19 | Phase 2.3-2.5 完成：WeigherAgent, CompressorAgent, DataFactoryPipeline ✨ |

---

## 11. 贡献者

本项目由 AI 助手协助开发，基于需求文档 [req1.md](config/project1/req1.md) 和交付计划 [del1.md](config/project1/del1.md) 实现。

---

## 12. 许可证

（待定）

---

**文档维护**: 请在每次重大更新后同步更新本文档  
**最后更新**: 2026年1月19日
