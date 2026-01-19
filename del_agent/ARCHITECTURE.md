# AI导师评价交互网络 - 系统架构文档

**版本**: v3.0.0
**更新日期**: 2026年1月19日
**状态**: Phase 3 前端交互层已完成初版

---

## 1. 系统概览

本系统是一个基于多智能体架构的AI导师评价处理与交互平台，采用**双层设计**：
- **前端交互层**：基于用户画像的个性化交互与意图路由
- **后端数据工厂**：将非结构化评论转化为结构化知识节点

### 1.1 核心特性

- ✅ **全流程智能体协作**：前端与后端共9个专用智能体协同工作
- ✅ **个性化交互引擎**：基于动态用户画像的风格自适应回复
- ✅ **意图驱动路由**：自动识别闲聊、查询与信息提交意图
- ✅ **模块化智能体架构**：基于 `BaseAgent` 的统一接口
- ✅ **核验循环机制**：通过 `CriticAgent` 实现质量控制
- ✅ **多模型支持**：统一的 LLM 接口（OpenAI、DeepSeek、Moonshot、豆包等）

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端交互层 (Frontend Layer)                     │
│                                                                         │
│   [ 用户输入 (Text/Voice) ]                                              │
│         │                                                               │
│         ▼                                                               │
│   ┌───────────────┐        ┌──────────────────┐    ┌─────────────────┐  │
│   │ VoiceAdapter  │───────►│ InfoExtractor    │    │ UserProfile     │  │
│   │ (语音/文本)    │        │ Agent (意图识别)  │◄───┤ Manager         │  │
│   └───────────────┘        └─────────┬────────┘    │ (画像管理)       │  │
│                                      │             └────────┬────────┘  │
│         ┌────────────────────────────┼──────────────────────┘           │
│         │                            │                                  │
│         ▼                            ▼                                  │
│   ┌───────────────┐        ┌──────────────────┐    ┌─────────────────┐  │
│   │ Frontend      │───────►│ PersonaAgent     │◄───┤ Conversation    │  │
│   │ Orchestrator  │        │ (个性化回复)      │    │ Context         │  │
│   │ (中枢控制器)   │        └─────────▲────────┘    │ (会话历史)       │  │
│   └───────────────┘                  │             └─────────────────┘  │
│         │                            │                                  │
│         │ (提供信息意图)              │ (查询意图/RAG)                    │
└─────────┼────────────────────────────┼──────────────────────────────────┘
          │ RawReview                  │ Context/Knowledge
          ▼                            ▲
┌─────────────────────────────────────────────────────────────────────────┐
│                          后端数据工厂 (Backend Data Factory)              │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │           DataFactoryPipeline (流水线控制器)                        │  │
│  │                                                                   │  │
│  │   RawReview → Cleaner → Decoder → Weigher → Compressor            │  │
│  │                  ↓          ↓         ↓          ↓                 │  │
│  │              CriticAgent (核验循环，可选保质机制)                     │  │
│  └──────────────────┬────────────────────────────────────────────────┘  │
│                     │ StructuredKnowledgeNode                           │
│                     ▼                                                   │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      存储与记忆 (Storage & Memory)                  │  │
│  │                                                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │  │
│  │  │ VectorStore  │  │ Knowledge    │  │ Dictionary   │             │  │
│  │  │ (向量检索)    │  │ Graph        │  │ Store        │             │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                             核心基础设施 (Core Infrastructure)            │
│                                                                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │   BaseAgent    │  │ LLMProvider    │  │ PromptManager  │             │
│  │  (智能体基类)   │  │ (多模型适配)    │  │ (模板管理)      │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心组件说明

### 3.1 前端交互层 (Frontend Layer)

#### 3.1.1 FrontendOrchestrator
**文件**: [frontend/orchestrator.py](frontend/orchestrator.py)

**功能**：
- 前端交互的中央枢纽
- 协调意图识别、RAG检索、后端流水线调用
- 维护用户会话上下文

**处理流程**：
1. 接收用户输入（`process_user_input`）
2. 调用 **InfoExtractorAgent** 识别意图
3. 根据意图路由：
   - **Chat/Query**: 检索上下文 → 调用 **PersonaAgent** 生成回复
   - **Info Submission**: 调用后端流水线处理 RawReview → 确认并回复

#### 3.1.2 InfoExtractorAgent
**文件**: [agents/info_extractor.py](agents/info_extractor.py)

**功能**：
- 识别用户输入的三类意图：`chat` (闲聊), `query` (查询), `provide_info` (提供信息)
- 提取关键实体（导师名、学校、维度等）
- 将用户评价转化为 `RawReview` 结构化对象

#### 3.1.3 PersonaAgent
**文件**: [agents/persona.py](agents/persona.py)

**功能**：
- 最终回复生成器
- 根据 **UserPersonalityVector** 调整语言风格（幽默度、正式度、简洁度）
- 整合 RAG 检索到的知识片段

#### 3.1.4 UserProfileManager
**文件**: [frontend/user_profile.py](frontend/user_profile.py)

**功能**：
- 管理用户画像 (`UserPersonalityVector`)
- 基于交互历史动态更新用户偏好
- 计算并维护风格权重

---

### 3.2 后端数据工厂 (Backend Data Factory)

#### 3.2.1 DataFactoryPipeline
**文件**: [backend/factory.py](backend/factory.py)

**功能**：
- 编排所有后端智能体的执行顺序
- 封装非结构化数据到结构化知识的完整ETL过程

#### 3.2.2 RawCommentCleaner（清洗智能体）
**文件**: [agents/raw_comment_cleaner.py](agents/raw_comment_cleaner.py)

**功能**：
- 去除情绪化表达，提取客观事实
- 评估情绪强度，保留关键信息

#### 3.2.3 SlangDecoderAgent（黑话解码智能体）
**文件**: [agents/slang_decoder.py](agents/slang_decoder.py)

**功能**：
- 识别并翻译学术圈黑话（如"学术妲己"、"画饼"）
- 维护动态词典，提升语义理解准确度

#### 3.2.4 WeigherAgent（权重分析智能体）
**文件**: [agents/weigher.py](agents/weigher.py)

**功能**：
- 多维度评分算法：身份可信度(50%) + 时间衰减(30%) - 离群惩罚(20%)
- 计算信息的置信度权重 `weight_score`

#### 3.2.5 CompressorAgent（结构化压缩智能体）
**文件**: [agents/compressor.py](agents/compressor.py)

**功能**：
- 将处理后的信息映射到标准知识图谱维度（9大维度）
- 生成最终的 `StructuredKnowledgeNode`

#### 3.2.6 CriticAgent（核验智能体）
**文件**: [agents/critic.py](agents/critic.py)

**功能**：
- 可选的质量控制节点
- 对其他Agent的输出进行核验和打分

---

### 3.3 核心基础设施 (Core Infrastructure)

#### 3.3.1 BaseAgent
**文件**: [core/base_agent.py](core/base_agent.py)

**功能**：
- 所有智能体的基类，提供统一的 `process` 和 `process_with_verification` 接口

#### 3.3.2 LLMProvider
**文件**: [core/llm_adapter.py](core/llm_adapter.py)

**功能**：
- 统一模型接口，支持 **OpenAI**, **DeepSeek**, **Moonshot**, **Doubao** 等

---

## 4. 数据流示例 (Data Flow)

### 4.1 完整交互流程（信息提交场景）

**用户输入**：
> "我就读于X大学，导师张三虽然学术水平高，但性格太push了，经常半夜发消息，感觉压力很大。"

**Step 1: 前端处理**
1. **InfoExtractor**: 
   - 意图识别 -> `provide_info`
   - 实体提取 -> `Mentor: 张三`, `School: X大学`
   - 生成 -> `RawReview(...)`
2. **Orchestrator**: 将 RawReview 发送给后端流水线

**Step 2: 后端处理**
1. **Cleaner**: 提取事实 "学术水平高，但工作强度大，经常非工作时间联系"
2. **Decoder**: (无特定黑话，保持原意)
3. **Weigher**: 计算权重分数 (例如 0.85)
4. **Compressor**: 归类维度 `Work_Pressure`, `Personality` -> 生成 `StructuredKnowledgeNode`

**Step 3: 响应生成**
1. **Orchestrator**: 接收后端处理成功信号
2. **PersonaAgent**: 根据用户画像（如偏好简洁）生成回复
   - *回复*: "收到，已记录关于张三导师的工作压力评价。感谢分享这些细节，这对其他同学参考很有价值。"

---

## 5. 项目结构映射

```
del_agent/
├── agents/                 # 智能体实现
│   ├── compressor.py
│   ├── critic.py
│   ├── info_extractor.py   # [Frontend]
│   ├── persona.py          # [Frontend]
│   ├── raw_comment_cleaner.py
│   ├── slang_decoder.py
│   └── weigher.py
├── backend/                # 后端流水线
│   └── factory.py
├── config/                 # 配置文件
├── core/                   # 核心基础类
│   ├── base_agent.py
│   └── llm_adapter.py
├── frontend/               # 前端交互层
│   ├── orchestrator.py     # 核心编排器
│   ├── user_profile.py     # 画像管理
│   └── voice_adapter.py    # 语音适配
├── memory/                 # 记忆管理
├── models/                 # Pydantic模型schema
└── storage/                # 数据存储实现
```

---

## 6. 版本历史

| 版本 | 日期       | 更新内容                               |
| ---- | ---------- | -------------------------------------- |
| v1.0 | 2024-Q1    | 初始版本，基础框架                     |
| v2.0 | 2026-01    | Phase 1 完成：核验循环和数据模型       |
| v2.3 | 2026-01-19 | Phase 2 完成：后端数据工厂全流程       |
| v3.0 | 2026-01-20 | Phase 3 完成：前端交互层与全链路打通 ✨ |

