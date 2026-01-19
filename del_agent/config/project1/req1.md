
# 系统架构设计说明书：AI导师评价交互网络

## 1. 总体架构设计 (High-Level Architecture)

系统采用 **双层多智能体架构 (Two-Layer Multi-Agent System)**，分为 **后端数据工厂 (Backend Data Factory)** 和 **前端交互层 (Frontend Interaction Layer)**。两者通过结构化知识库（Structured Knowledge Base）和异步消息队列进行解耦。

### 技术选型建议 (给Coding Agent的默认设定)
*   **框架**: LangGraph / LangChain (用于构建有向图和循环机制)
*   **数据库**: Vector DB (用于语义检索) + Relational DB (用于存储结构化权重和元数据)
*   **通信**: Pub/Sub 模式 (用于前端向后端回传新信息)

---

## 2. 模块详细定义

### 模块 A: 后端数据工厂 (The Backend)
**目标**: 将非结构化文本转化为加权、多维度的结构化知识图谱。

#### 核心组件设计
1.  **数据流控制器 (Pipeline Controller)**
    *   **功能**: 管理数据流转，实例化各个Agent，处理错误。
    *   **关键逻辑**: 实现`Verification Loop` (核验循环)，即：`Agent Output` -> `Critic Check` -> `Pass/Retry`。

2.  **智能体群 (Backend Agents)**
    我们需要定义一个基类 `BaseBackendAgent`，并通过以下子类实现：
    *   **CleanerAgent (清洗/去极化)**: 负责去除情绪化表达，保留事实核心。
    *   **SlangDecoderAgent (黑话解码)**: 识别并翻译特定圈子术语，维护动态的`SlangDictionary`。
    *   **WeighterAgent (权重分析)**: 计算信息可信度。
        *   *算法逻辑*: `Score = f(IdentityConfidence, TimeDecay, OutlierStatus)`
    *   **CompressorAgent (结构化/压缩)**: 将处理后的信息映射到标准Schema。
    *   **CriticAgent (判别节点)**:
        *   *输入*: 上游Agent的输出 + 原始Context。
        *   *输出*: `Bool is_valid`, `String feedback`.
        *   *参数*: `strictness_level` (可调节的严格度阈值).

3.  **多维串联器 (Dimension Linker)**
    *   **功能**: 也就是“行业地图”构建者。
    *   **逻辑**: 定期运行的任务，对已入库数据进行聚类（Clustering），建立 Tag 之间的关联（如：`Title: 教授` <-> `Pressure: High`）。

### 模块 B: 前端交互层 (The Frontend)
**目标**: 基于用户画像的个性化交互与信息路由。

#### 核心组件设计
1.  **UserProfileManager (用户画像管理器)**
    *   维护 `UserPersonalityVector` (性格向量) 和 `UserInterests` (关注点)。
    *   根据交互历史动态更新。

2.  **FrontendOrchestrator (前端编排器)**
    *   **Router**: 判断用户意图（是闲聊、查询、还是提供信息）。
    *   **Filter (价值观过滤器)**: 根据预设安全策略过滤内容。

3.  **PersonaAgent (人设交互智能体)**
    *   **功能**: 生成最终回复。
    *   **输入**: 后端检索到的结构化数据 + 黑话词典 + 用户性格向量 + 对话历史。
    *   **特性**: 必须包含 `StyleModulator` (风格调节器)，根据用户性格调整“梗”的浓度和严肃程度。

4.  **InfoExtractorAgent (信息抽取器)**
    *   **功能**: 旁路监听。从用户对话中提取新的评价信息，发送至后端数据工厂。

---

## 3. 数据结构定义 (Data Schemas)

为了让Coding Agent写出准确的代码，必须预定义数据对象：

```python
# 1. 原始评价数据
class RawReview:
    content: str
    source_metadata: dict  # 包含时间、来源平台、发布者ID
    timestamp: datetime

# 2. 结构化知识单元 (后端的产出)
class StructuredKnowledgeNode:
    mentor_id: str
    dimension: str       # e.g., "Funding", "Personality", "Academic_Geng"
    fact_content: str    # 去极化后的事实
    original_nuance: str # 保留的“黑话”或原文特色
    weight_score: float  # 0.0 - 1.0
    tags: List[str]
    last_updated: datetime

# 3. 判别反馈 (核验节点的输出)
class CriticFeedback:
    is_approved: bool
    reasoning: str
    suggestion: str      # 如果不通过，给出的修改建议
```

---

## 4. Coding Agent 的逐步实现路线图 (Implementation Roadmap)

请按照以下步骤生成代码，每一步都需要是可运行的独立模块：

**Step 1: 基础设施搭建 (Infrastructure)**
*   定义上述 Python Data Classes (`Schema`)。
*   建立 `VectorDB` 和 `KnowledgeGraph` 的模拟接口（Mock Interface）。
*   实现通用的 `VerificationLoop` 函数（接收一个生成函数和一个判别函数，实现重试逻辑）。

**Step 2: 后端流水线实现 (Backend Pipeline)**
*   实现 `CleanerAgent` 和 `SlangDecoderAgent`。
*   实现 `CriticAgent`，并将其挂载到上述 Agent 的输出端。
*   实现 `WeighterAgent` 的权重计算逻辑。
*   编写一个 `process_raw_data(raw_review)` 主流程函数，串联这些 Agent。

**Step 3: 前端交互实现 (Frontend Interaction)**
*   实现 `UserProfileManager`。
*   构建 `PersonaAgent`，使其 prompt 能够接受 `style` 参数。
*   实现 RAG (Retrieval-Augmented Generation) 流程：用户Query -> 检索 KnowledgeNode -> 注入 PersonaAgent -> 生成回复。

**Step 4: 闭环与整合 (System Integration)**
*   实现 `InfoExtractorAgent`：将前端对话转化为 `RawReview` 并输入后端。
*   编写 `main.py` 模拟一个完整的“用户输入 -> 后端处理 -> 前端回答 -> 用户反馈 -> 后端更新”的流程。