# AI导师评价交互网络 - 系统融合设计方案

## 文档版本
- **版本号**: v1.0
- **创建日期**: 2026年1月19日
- **状态**: 设计阶段

---

## 第一部分：现有框架分析

### 1.1 当前架构总结

现有的 `del_agent` 框架已经建立了一个**模块化的智能体架构**，包含以下核心组件：

#### 核心层 (Core Layer)
1. **BaseAgent** (`core/base_agent.py`)
   - 抽象基类，定义统一的智能体接口
   - 生命周期管理：初始化、准备输入、处理、验证输出
   - 统计信息追踪：执行次数、执行时间
   - **关键方法**：
     - `process(raw_input, **kwargs)`: 主处理流程
     - `prepare_input()`: 输入数据预处理
     - `validate_output()`: 输出验证（基础版本）
     - `get_output_schema()`: 定义输出数据结构
     - `get_prompt_template_name()`: 获取提示词模板名称

2. **LLMProvider** (`core/llm_adapter.py`)
   - 支持多模型服务商（OpenAI、DeepSeek、Moonshot、豆包等）
   - 统一的调用接口：`generate()` 和 `generate_structured()`
   - 支持结构化输出（基于Pydantic模型）
   - 已集成重试机制（tenacity库）

3. **PromptManager** (`core/prompt_manager.py`)
   - 从 YAML/JSON 加载提示词模板
   - Jinja2 模板引擎支持变量替换
   - 缓存和预编译提高性能

#### 数据层 (Data Layer)
4. **Schemas** (`models/schemas.py`)
   - Pydantic 数据模型定义
   - 已有模型：
     - `CommentCleaningResult`: 评论清洗结果
     - `ProcessingStats`: 处理统计
     - `LLMConfig`: LLM配置
   - 内置数据验证（validator装饰器）

5. **ConfigManager** (`utils/config.py`)
   - 从 `settings.yaml` 加载配置
   - 支持环境变量覆盖
   - 管理 LLM 和 Agent 配置

#### 智能体层 (Agent Layer)
6. **RawCommentCleaner** (`agents/raw_comment_cleaner.py`)
   - 继承自 BaseAgent
   - 功能：去情绪化、提取事实、评估情绪强度、提取关键词
   - 输出：`CommentCleaningResult`
   - 支持批量处理：`analyze_batch()`

### 1.2 现有框架优势

✅ **已具备的能力**：
1. **模块化设计**：清晰的分层架构，易于扩展
2. **类型安全**：大量使用 Type Hinting 和 Pydantic
3. **可配置性**：YAML 配置 + 环境变量
4. **多模型支持**：统一的 LLM 接口
5. **批量处理**：已实现基础的批量处理能力
6. **日志追踪**：完善的日志系统
7. **错误处理**：基础的异常捕获和重试机制

### 1.3 与 req1.md 的差距分析

❌ **缺失的核心功能**：

#### 1.3.1 后端数据工厂部分
| 需求模块 | 现有实现 | 缺失内容 |
|---------|---------|---------|
| **CleanerAgent** | ✅ 已有 RawCommentCleaner | - |
| **SlangDecoderAgent** | ❌ 无 | 需新建黑话解码智能体 |
| **WeighterAgent** | ❌ 无 | 需新建权重分析智能体 |
| **CompressorAgent** | ❌ 无 | 需新建结构化压缩智能体 |
| **CriticAgent** | ❌ 无 | **核心缺失**：判别节点 |
| **Verification Loop** | ❌ 无 | **核心缺失**：核验循环机制 |
| **Pipeline Controller** | ❌ 无 | 需新建流水线控制器 |
| **Dimension Linker** | ❌ 无 | 需新建多维串联器 |

#### 1.3.2 前端交互层部分
| 需求模块 | 现有实现 | 缺失内容 |
|---------|---------|---------|
| **UserProfileManager** | ❌ 无 | 需新建用户画像管理器 |
| **FrontendOrchestrator** | ❌ 无 | 需新建前端编排器 |
| **PersonaAgent** | ❌ 无 | 需新建人设交互智能体 |
| **InfoExtractorAgent** | ❌ 无 | 需新建信息抽取器 |

#### 1.3.3 数据结构部分
| 需求模型 | 现有实现 | 缺失内容 |
|---------|---------|---------|
| **RawReview** | ❌ 无 | 需新建原始评价数据模型 |
| **StructuredKnowledgeNode** | ❌ 无 | 需新建结构化知识单元模型 |
| **CriticFeedback** | ❌ 无 | 需新建判别反馈模型 |
| **UserPersonalityVector** | ❌ 无 | 需新建用户性格向量模型 |

---

## 第二部分：融合设计方案

### 2.1 设计原则

🎯 **核心原则**：
1. **最小侵入性**：尽量扩展而非修改现有代码
2. **保持兼容性**：确保现有功能不受影响
3. **渐进式实现**：分阶段完成，每阶段可独立运行
4. **复用现有基础**：充分利用 BaseAgent、LLMProvider、PromptManager

### 2.2 架构融合策略

#### 2.2.1 对 BaseAgent 的增强

**当前 `BaseAgent.process()` 流程**：
```
Input → prepare_input() → render_prompt() → LLM.generate_structured() 
      → validate_output() → Return Result
```

**增强后的流程**（支持 Verification Loop）：
```
Input → prepare_input() → render_prompt() → LLM.generate_structured() 
      → validate_output() → [核验节点] → Pass/Retry → Return Result
                                ↓
                          CriticAgent Check
                                ↓
                    若不通过，重新生成（最多N次）
```

**实现方式**：
- **不修改** `BaseAgent.process()` 的核心逻辑
- **新增** `BaseAgent.process_with_verification()` 方法
- **新增** `VerificationLoop` 工具类（独立模块）

#### 2.2.2 模块化扩展路径

```
现有架构：
  core/
    ├── base_agent.py          [保持]
    ├── llm_adapter.py         [保持]
    └── prompt_manager.py      [保持]
  
  agents/
    └── raw_comment_cleaner.py [保持] → 对应 req1.md 的 CleanerAgent

新增模块：
  core/
    ├── verification.py        [新增] 核验循环核心逻辑
    └── pipeline.py            [新增] 流水线控制器
  
  agents/
    ├── slang_decoder.py       [新增] 黑话解码智能体
    ├── weigher.py             [新增] 权重分析智能体
    ├── compressor.py          [新增] 结构化压缩智能体
    ├── critic.py              [新增] 判别节点智能体
    ├── persona.py             [新增] 人设交互智能体
    └── info_extractor.py      [新增] 信息抽取器
  
  models/
    └── schemas.py             [扩展] 添加新的数据模型
  
  backend/                     [新增目录]
    ├── __init__.py
    ├── factory.py             [新增] 数据工厂主控制器
    └── dimension_linker.py    [新增] 多维串联器
  
  frontend/                    [新增目录]
    ├── __init__.py
    ├── orchestrator.py        [新增] 前端编排器
    └── user_profile.py        [新增] 用户画像管理
  
  storage/                     [新增目录]
    ├── __init__.py
    ├── vector_db.py           [新增] 向量数据库接口
    └── knowledge_graph.py     [新增] 知识图谱接口
```

---

## 第三部分：分步实现策略

### Phase 1: 核心基础设施（第1-2周）

**目标**：建立 Verification Loop 核心机制和扩展数据模型

#### Step 1.1: 数据模型扩展
**文件**: `models/schemas.py`

**新增模型**：
```python
# 1. 原始评价数据
class RawReview(BaseModel):
    content: str
    source_metadata: dict
    timestamp: datetime

# 2. 判别反馈
class CriticFeedback(BaseModel):
    is_approved: bool
    reasoning: str
    suggestion: str
    confidence_score: float  # 0.0-1.0

# 3. 结构化知识单元
class StructuredKnowledgeNode(BaseModel):
    mentor_id: str
    dimension: str
    fact_content: str
    original_nuance: str
    weight_score: float
    tags: List[str]
    last_updated: datetime

# 4. 黑话解码结果
class SlangDecodingResult(AgentResult):
    decoded_text: str
    slang_dictionary: Dict[str, str]
    confidence_score: float

# 5. 权重分析结果
class WeightAnalysisResult(AgentResult):
    weight_score: float
    identity_confidence: float
    time_decay: float
    outlier_status: bool
    reasoning: str

# 6. 压缩结果
class CompressionResult(AgentResult):
    structured_node: StructuredKnowledgeNode
```

**验证标准**：
- ✅ 所有模型通过 Pydantic 验证
- ✅ 编写单元测试（`tests/test_schemas.py`）

#### Step 1.2: 核验循环机制
**新建文件**: `core/verification.py`

**核心类**：
```python
class VerificationLoop:
    """
    核验循环器：实现 Agent Output → Critic Check → Pass/Retry 逻辑
    """
    def __init__(
        self, 
        max_retries: int = 3,
        strictness_level: float = 0.7
    ):
        self.max_retries = max_retries
        self.strictness_level = strictness_level
    
    def execute(
        self,
        generator_func: Callable[[], BaseModel],
        critic_func: Callable[[BaseModel, Any], CriticFeedback],
        context: Any = None
    ) -> Tuple[BaseModel, List[CriticFeedback]]:
        """
        执行核验循环
        
        Returns:
            (最终结果, 所有反馈历史)
        """
        feedback_history = []
        
        for attempt in range(self.max_retries):
            # 生成输出
            output = generator_func()
            
            # 判别检查
            feedback = critic_func(output, context)
            feedback_history.append(feedback)
            
            # 判断是否通过
            if feedback.is_approved:
                return output, feedback_history
            
            # 日志记录不通过原因
            logger.warning(f"Attempt {attempt+1} failed: {feedback.reasoning}")
        
        # 超过最大重试次数，返回最后一次结果
        logger.error(f"Verification failed after {self.max_retries} attempts")
        return output, feedback_history
```

**集成到 BaseAgent**：
在 `core/base_agent.py` 中新增方法：

```python
def process_with_verification(
    self,
    raw_input: Any,
    critic_agent: Optional['BaseAgent'] = None,
    max_retries: int = 3,
    **kwargs
) -> BaseModel:
    """
    带核验循环的处理流程
    """
    if critic_agent is None:
        # 无判别器，回退到标准流程
        return self.process(raw_input, **kwargs)
    
    verification_loop = VerificationLoop(max_retries=max_retries)
    
    def generator():
        return self.process(raw_input, **kwargs)
    
    def critic(output, context):
        return critic_agent.evaluate(output, context)
    
    result, feedback_history = verification_loop.execute(
        generator_func=generator,
        critic_func=critic,
        context=raw_input
    )
    
    # 附加反馈历史到元数据
    result.metadata['feedback_history'] = [fb.dict() for fb in feedback_history]
    return result
```

**验证标准**：
- ✅ 单元测试：模拟成功/失败场景
- ✅ 集成测试：使用 RawCommentCleaner + Mock CriticAgent

---

### Phase 2: 后端数据工厂（第3-5周）

**目标**：实现完整的后端处理流水线

#### Step 2.1: 判别节点智能体
**新建文件**: `agents/critic.py`

**功能**：
- 接收上游 Agent 的输出 + 原始输入
- 判断是否符合质量标准
- 返回 `CriticFeedback`

**提示词模板**: `prompts/templates/critic.yaml`

**关键设计**：
```python
class CriticAgent(BaseAgent):
    def __init__(
        self,
        llm_provider,
        strictness_level: float = 0.7,
        **kwargs
    ):
        super().__init__(name="CriticAgent", llm_provider=llm_provider, **kwargs)
        self.strictness_level = strictness_level
    
    def evaluate(
        self, 
        agent_output: BaseModel, 
        original_input: Any
    ) -> CriticFeedback:
        """
        评估 Agent 输出质量
        
        Args:
            agent_output: 待评估的输出
            original_input: 原始输入（用于对比）
        
        Returns:
            CriticFeedback
        """
        # 构建评估提示词
        evaluation_context = {
            "agent_output": agent_output.dict(),
            "original_input": str(original_input),
            "strictness_level": self.strictness_level
        }
        
        # 调用 LLM 进行判别
        feedback = self.process(evaluation_context)
        return feedback
```

**验证标准**：
- ✅ 能够正确识别高质量输出（通过率 > 90%）
- ✅ 能够拒绝低质量输出（误判率 < 10%）

#### Step 2.2: 黑话解码智能体
**新建文件**: `agents/slang_decoder.py`

**功能**：
- 识别网络黑话、行业术语、隐喻表达
- 维护动态的 `SlangDictionary`（持久化存储）
- 输出解码后的文本 + 黑话词典

**关键设计**：
```python
class SlangDecoderAgent(BaseAgent):
    def __init__(
        self,
        llm_provider,
        slang_dict_path: Path = None,
        **kwargs
    ):
        super().__init__(name="SlangDecoder", llm_provider=llm_provider, **kwargs)
        self.slang_dictionary = self._load_slang_dict(slang_dict_path)
    
    def _load_slang_dict(self, path: Path) -> Dict[str, str]:
        """从文件加载黑话词典"""
        if path and path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def update_dictionary(self, new_terms: Dict[str, str]):
        """动态更新黑话词典"""
        self.slang_dictionary.update(new_terms)
        self._save_slang_dict()
```

**验证标准**：
- ✅ 识别常见学术黑话（如"学术妲己"、"画饼"等）
- ✅ 词典能够持久化并动态更新

#### Step 2.3: 权重分析智能体
**新建文件**: `agents/weigher.py`

**功能**：
- 计算信息可信度评分
- 算法：`Score = f(IdentityConfidence, TimeDecay, OutlierStatus)`

**关键设计**：
```python
class WeigherAgent(BaseAgent):
    def calculate_weight(
        self,
        identity_confidence: float,
        time_decay: float,
        outlier_status: bool
    ) -> float:
        """
        权重计算公式
        
        Formula:
            base_score = identity_confidence * 0.5 + time_decay * 0.3
            outlier_penalty = 0.2 if outlier_status else 0
            final_score = max(0, base_score - outlier_penalty)
        """
        base_score = identity_confidence * 0.5 + time_decay * 0.3
        outlier_penalty = 0.2 if outlier_status else 0
        return max(0.0, min(1.0, base_score - outlier_penalty))
```

#### Step 2.4: 结构化压缩智能体
**新建文件**: `agents/compressor.py`

**功能**：
- 将处理后的信息映射到 `StructuredKnowledgeNode`
- 提取维度标签（Funding、Personality、Academic_Geng 等）

#### Step 2.5: 流水线控制器
**新建文件**: `backend/factory.py`

**功能**：
- 编排所有后端 Agent 的执行顺序
- 管理 Verification Loop
- 错误处理和恢复

**关键设计**：
```python
class DataFactoryPipeline:
    """
    后端数据工厂流水线
    
    流程：
    RawReview → CleanerAgent → SlangDecoderAgent → WeigherAgent 
              → CompressorAgent → StructuredKnowledgeNode
              
    每个步骤都可选配 CriticAgent 进行核验
    """
    def __init__(
        self,
        llm_provider,
        enable_verification: bool = True,
        max_retries: int = 3
    ):
        self.cleaner = RawCommentCleaner(llm_provider)
        self.decoder = SlangDecoderAgent(llm_provider)
        self.weigher = WeigherAgent(llm_provider)
        self.compressor = CompressorAgent(llm_provider)
        
        if enable_verification:
            self.critic = CriticAgent(llm_provider)
        else:
            self.critic = None
        
        self.max_retries = max_retries
    
    def process_raw_review(
        self, 
        raw_review: RawReview
    ) -> StructuredKnowledgeNode:
        """
        处理原始评价数据
        
        Returns:
            结构化知识节点
        """
        # Step 1: 清洗
        if self.critic:
            cleaned = self.cleaner.process_with_verification(
                raw_review.content,
                critic_agent=self.critic,
                max_retries=self.max_retries
            )
        else:
            cleaned = self.cleaner.process(raw_review.content)
        
        # Step 2: 解码黑话
        decoded = self.decoder.process(cleaned.factual_content)
        
        # Step 3: 计算权重
        weight_result = self.weigher.process({
            "content": decoded.decoded_text,
            "metadata": raw_review.source_metadata
        })
        
        # Step 4: 结构化压缩
        knowledge_node = self.compressor.process({
            "factual_content": decoded.decoded_text,
            "weight_score": weight_result.weight_score,
            "keywords": cleaned.keywords,
            "original_nuance": raw_review.content[:50] + "..."
        })
        
        return knowledge_node.structured_node
```

**验证标准**：
- ✅ 端到端测试：输入 RawReview，输出 StructuredKnowledgeNode
- ✅ 性能测试：处理 100 条评论 < 5 分钟
- ✅ 验证循环统计：记录通过率和平均重试次数

---

### Phase 3: 前端交互层（第6-7周）

**目标**：实现个性化交互和信息回传

#### Step 3.1: 用户画像管理器
**新建文件**: `frontend/user_profile.py`

**数据模型**：
```python
class UserPersonalityVector(BaseModel):
    humor_tolerance: float = 0.5      # 梗的接受度
    formality_preference: float = 0.5  # 正式程度偏好
    detail_level: float = 0.5          # 详细程度偏好
    interests: List[str] = []          # 关注点
    interaction_history: List[dict] = []

class UserProfileManager:
    def __init__(self, storage_path: Path):
        self.profiles: Dict[str, UserPersonalityVector] = {}
    
    def update_profile(self, user_id: str, interaction: dict):
        """根据交互历史动态更新用户画像"""
        pass
    
    def get_style_params(self, user_id: str) -> dict:
        """获取适用于该用户的风格参数"""
        profile = self.profiles.get(user_id)
        return {
            "humor_level": profile.humor_tolerance,
            "formality": profile.formality_preference,
            "detail": profile.detail_level
        }
```

#### Step 3.2: 人设交互智能体
**新建文件**: `agents/persona.py`

**功能**：
- 根据用户画像调整回复风格
- 集成 RAG（检索增强生成）
- `StyleModulator`：风格调节器

**关键设计**：
```python
class PersonaAgent(BaseAgent):
    def __init__(
        self,
        llm_provider,
        vector_db,  # 用于检索
        slang_dictionary: dict,
        **kwargs
    ):
        super().__init__(name="PersonaAgent", llm_provider=llm_provider, **kwargs)
        self.vector_db = vector_db
        self.slang_dict = slang_dictionary
    
    def generate_response(
        self,
        user_query: str,
        user_profile: UserPersonalityVector,
        conversation_history: List[dict] = None
    ) -> str:
        """
        生成个性化回复
        
        流程：
        1. 检索相关知识节点（RAG）
        2. 根据用户画像调整风格
        3. 生成回复
        """
        # RAG 检索
        relevant_knowledge = self.vector_db.search(user_query, top_k=5)
        
        # 风格参数
        style_params = {
            "humor_level": user_profile.humor_tolerance,
            "use_slang": user_profile.humor_tolerance > 0.6,
            "formality": user_profile.formality_preference
        }
        
        # 构建提示词
        context = {
            "query": user_query,
            "knowledge_base": relevant_knowledge,
            "style_params": style_params,
            "conversation_history": conversation_history or []
        }
        
        response = self.process(context)
        return response.content
```

#### Step 3.3: 信息抽取器
**新建文件**: `agents/info_extractor.py`

**功能**：
- 旁路监听用户对话
- 提取新的评价信息
- 发送至后端数据工厂

#### Step 3.4: 前端编排器
**新建文件**: `frontend/orchestrator.py`

**功能**：
- 路由器：判断用户意图（闲聊/查询/提供信息）
- 价值观过滤器：内容安全检查
- 协调 PersonaAgent 和 InfoExtractor

---

### Phase 4: 数据存储与整合（第8周）

**目标**：实现数据持久化和系统闭环

#### Step 4.1: 向量数据库接口
**新建文件**: `storage/vector_db.py`

**Mock 实现**（生产环境可替换为 Milvus/Pinecone）：
```python
class VectorDatabase:
    def __init__(self, embedding_model=None):
        self.embeddings = {}  # id -> vector
        self.metadata = {}    # id -> metadata
    
    def insert(self, node: StructuredKnowledgeNode):
        """插入知识节点"""
        pass
    
    def search(self, query: str, top_k: int = 5) -> List[StructuredKnowledgeNode]:
        """语义检索"""
        pass
```

#### Step 4.2: 知识图谱接口
**新建文件**: `storage/knowledge_graph.py`

**功能**：
- 维护导师-维度-标签关系
- 支持多维串联器的聚类分析

#### Step 4.3: 主流程整合
**新建文件**: `main.py`（替换现有的 `examples/demo.py`）

**完整闭环**：
```python
def main():
    # 1. 初始化后端
    backend = DataFactoryPipeline(llm_provider, enable_verification=True)
    vector_db = VectorDatabase()
    
    # 2. 初始化前端
    user_profile_mgr = UserProfileManager(storage_path="./data/profiles")
    persona_agent = PersonaAgent(llm_provider, vector_db)
    orchestrator = FrontendOrchestrator(persona_agent, user_profile_mgr)
    
    # 3. 模拟用户交互循环
    user_id = "test_user_001"
    
    while True:
        user_input = input("用户: ")
        
        # 前端处理
        response = orchestrator.handle_input(user_id, user_input)
        print(f"助手: {response}")
        
        # 后台：检查是否包含新的评价信息
        extracted_review = orchestrator.info_extractor.extract(user_input)
        if extracted_review:
            # 异步发送到后端处理
            knowledge_node = backend.process_raw_review(extracted_review)
            vector_db.insert(knowledge_node)
            print("[系统] 新增知识节点已入库")
```

---

## 第四部分：技术细节与注意事项

### 4.1 Verification Loop 的性能优化

**问题**：频繁调用 LLM 会导致成本和延迟增加

**优化策略**：
1. **自适应重试**：根据历史通过率动态调整 `max_retries`
2. **缓存机制**：相同输入的判别结果可缓存（TTL=1小时）
3. **并行验证**：批量处理时，多个 Agent 并行执行
4. **降级策略**：若判别器超时，自动回退到无验证模式

### 4.2 Prompt Engineering 要点

**CriticAgent 提示词设计**：
```yaml
system_prompt: |
  你是一个严格的质量检查员。请评估以下 Agent 输出是否符合标准。
  
  评估标准：
  1. 事实准确性（与原文是否一致）
  2. 信息完整性（是否遗漏关键信息）
  3. 格式正确性（是否符合 Schema 定义）
  
  严格度等级：{{ strictness_level }}
  - 0.5：宽松（允许轻微偏差）
  - 0.7：标准（正常质量要求）
  - 0.9：严格（要求近乎完美）
  
  输出格式：
  {
    "is_approved": true/false,
    "reasoning": "详细原因",
    "suggestion": "改进建议（若不通过）",
    "confidence_score": 0.85
  }
```

### 4.3 Type Hinting 规范

**所有新增代码必须遵守**：
```python
from typing import List, Dict, Optional, Tuple, Callable, Any, Union
from pathlib import Path

# ✅ 正确示例
def process_data(
    input_data: List[RawReview],
    config: Optional[Dict[str, Any]] = None,
    callback: Callable[[str], None] = None
) -> Tuple[List[StructuredKnowledgeNode], ProcessingStats]:
    ...

# ❌ 错误示例（缺少类型注解）
def process_data(input_data, config=None):
    ...
```

### 4.4 测试策略

**每个 Phase 完成后必须通过的测试**：

1. **单元测试**：每个 Agent 独立测试
   - 输入验证
   - 输出格式验证
   - 异常处理

2. **集成测试**：Agent 之间的协作
   - Cleaner + Critic 的核验循环
   - 完整流水线测试

3. **性能测试**：
   - 单条数据处理时间 < 5秒
   - 批量处理（100条）< 5分钟
   - 内存占用 < 500MB

4. **端到端测试**：
   - 用户输入 → 后端处理 → 前端回复 → 信息回传

---

## 第五部分：实施时间表

| Phase | 时间 | 关键交付物 | 验收标准 |
|-------|------|-----------|---------|
| **Phase 1** | 第1-2周 | `verification.py` + 扩展 `schemas.py` | ✅ 核验循环单元测试通过 |
| **Phase 2.1** | 第3周 | `CriticAgent` + 提示词模板 | ✅ 判别准确率 > 85% |
| **Phase 2.2-2.4** | 第4周 | SlangDecoder、Weigher、Compressor | ✅ 每个 Agent 单元测试通过 |
| **Phase 2.5** | 第5周 | `DataFactoryPipeline` | ✅ 端到端流水线测试通过 |
| **Phase 3** | 第6-7周 | 前端模块 + PersonaAgent | ✅ 个性化交互演示成功 |
| **Phase 4** | 第8周 | 数据存储 + 闭环整合 | ✅ 完整系统演示 |

---

## 第六部分：风险与应对

### 6.1 技术风险

| 风险项 | 概率 | 影响 | 应对措施 |
|-------|------|------|---------|
| LLM 调用失败率高 | 中 | 高 | 增加重试机制、降级策略 |
| 核验循环成本过高 | 高 | 中 | 引入缓存、自适应重试 |
| 向量数据库性能瓶颈 | 低 | 高 | 初期使用 Mock，后期迁移专业方案 |
| Prompt 设计不当导致质量差 | 中 | 高 | 建立 Prompt 评估体系，快速迭代 |

### 6.2 设计风险

| 风险项 | 概率 | 影响 | 应对措施 |
|-------|------|------|---------|
| 过度设计（功能过于复杂） | 中 | 中 | 分阶段实现，每阶段可独立运行 |
| 兼容性问题（破坏现有功能） | 低 | 高 | 保持向后兼容，新功能作为扩展 |
| 性能不达标 | 中 | 中 | 引入性能监控，早期发现瓶颈 |

---

## 第七部分：下一步行动

### 7.1 立即行动项（本周）

1. ✅ **完成本文档** → 已完成
2. ⏭️ **创建分支**：`git checkout -b feature/verification-loop`
3. ⏭️ **开始 Phase 1.1**：扩展 `models/schemas.py`
   - 新增 6 个数据模型
   - 编写单元测试
4. ⏭️ **开始 Phase 1.2**：实现 `core/verification.py`
   - 核心类 `VerificationLoop`
   - 集成到 `BaseAgent`

### 7.2 本周目标

- [ ] 完成所有数据模型定义
- [ ] 核验循环基础功能可运行
- [ ] 编写并通过所有单元测试
- [ ] 更新 `README.md`，说明新增功能

### 7.3 沟通与协作

**定期同步**：
- 每周五：提交阶段性成果 + 演示
- 遇到技术难点：及时沟通，调整方案

**文档维护**：
- 每个 Phase 完成后，更新本文档的"实施进度"章节
- API 文档自动生成（使用 Sphinx 或 mkdocs）

---

## 附录：术语表

| 术语 | 定义 |
|-----|------|
| **Verification Loop** | 核验循环，指生成输出 → 判别检查 → 通过/重试的迭代流程 |
| **CriticAgent** | 判别节点智能体，负责评估其他 Agent 的输出质量 |
| **RAG** | Retrieval-Augmented Generation，检索增强生成 |
| **SlangDictionary** | 黑话词典，存储网络术语及其标准翻译 |
| **StructuredKnowledgeNode** | 结构化知识节点，后端处理后的标准化数据格式 |
| **PersonalityVector** | 性格向量，表示用户偏好的多维度参数 |

---

## 文档变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-01-19 | 初始版本，完成需求分析和设计方案 | System Architect |

---

**下一步**：请审阅本文档，确认设计方案后，即可开始 Phase 1 的代码实现。
