# del_agent 规划文档 v2（del2）

## 0. 范围与约束（必须遵守）
- 需求依据：req1.md + del1.md。
- 已完成：Phase 1（模型+核验循环）、Phase 2（后端工厂全链路）。
- 向量数据库与知识图谱已通过 Mem0 框架实现，无需重复建设，只做集成与接口对齐。
- 前端需同时支持：
  - 文本→文本交互（按 del1.md 设计）
  - 端到端语音模型（语音输入→语音输出），参照 doubao_sample 实现

## 1. 当前进度（简明）
- ✅ Phase 1：schemas 扩展、Verification Loop、BaseAgent 集成与测试
- ✅ Phase 2.1：CriticAgent + strictness 机制 + 测试
- ✅ Phase 2.2：SlangDecoderAgent + 词典存储（JSON/Mem0）+ 测试
- ✅ Phase 2.3-2.5：WeigherAgent、CompressorAgent、DataFactoryPipeline + 测试
- ✅ 后端处理流水线端到端测试通过
- ✅ Mem0：向量检索/知识图谱已有实现（可直接接入）
- ✅ Phase 3.1：补齐前端数据模型（UserPersonalityVector、InfoExtractResult）
- ✅ Phase 3.2：用户画像管理器（UserProfileManager）完成并测试通过
- ✅ Phase 3.3：PersonaAgent（个性化对话智能体）完成并测试通过
- ✅ Phase 3.4：InfoExtractorAgent（信息提取智能体）完成并测试通过
- ✅ Phase 3.5：FrontendOrchestrator（路由器）完成并测试通过 - 文本端到端流程已打通
- ✅ Phase 4.1：VoiceAdapter（语音适配器）完成并测试通过（12/12）
- ✅ Phase 4.2：双通道入口（main.py）完成 - 文本/语音模式均可独立运行
- ✅ Phase 5.1：VectorStore（向量存储接口）完成并测试通过（10/10）
- ✅ Phase 5.2：KnowledgeGraph（知识图谱接口）完成并测试通过（16/16）

## 2. 后续执行计划（可直接执行）

### Phase 3：前端交互层（文本模式 + 语音兼容）
**目标**：在不破坏文本流程的前提下，引入语音端到端适配层。

#### Step 3.1：补齐前端数据模型与接口（若缺失）
**文件**：models/schemas.py
- 补充/确认：UserPersonalityVector、InfoExtractResult（如已有则跳过）

**验收**：Pydantic 验证通过 + 单元测试

#### Step 3.2：用户画像管理器
**文件**：frontend/user_profile.py
- UserProfileManager：
  - update_profile(user_id, interaction)
  - get_style_params(user_id)
  - load/save（本地 JSON 或 Mem0）

**验收**：基础读写与更新策略测试

#### Step 3.3：PersonaAgent（文本模式）
**文件**：agents/persona.py
- 输入：query + UserPersonalityVector + conversation_history + RAG 结果
- 输出：文本回复
- StyleModulator：根据 profile 调整幽默度/正式度/细节量

**验收**：单元测试 + 最小可用对话示例

#### Step 3.4：InfoExtractorAgent（文本模式）
**文件**：agents/info_extractor.py
- 从用户对话中提取 RawReview
- 输出结构化 RawReview

**验收**：抽取成功率与边界用例测试

#### Step 3.5：FrontendOrchestrator（路由器）✅ 已完成
**文件**：frontend/orchestrator.py
- Router：闲聊 / 查询 / 提供信息
- 调度：PersonaAgent + InfoExtractorAgent + 后端 DataFactoryPipeline

**验收**：文本端到端流程可跑通 ✅
- 16/16 测试通过
- 三种意图路由正常工作
- 用户画像自动更新
- 多轮对话上下文维护

**实施日期**：2026-01-19
**报告**：del_agent/config/project1/result_report/phase3.5_result.md

---

### Phase 4：语音端到端适配层（兼容已实现语音模型）✅ 已完成
**目标**：集成 doubao_sample 的端到端语音对话能力，复用其 WebSocket 实时语音交互实现。

#### Step 4.1：语音适配器 ✅ 已完成
**文件**：frontend/voice_adapter.py（新增）
- 集成 doubao_sample 的端到端语音对话实现：
  - 音频输入→直接发送到语音服务
  - 语音服务→直接返回音频输出
  - 无需客户端实现 ASR/TTS（服务端集成）
- 与 FrontendOrchestrator 对接：
  - 语音模式：使用端到端语音对话
  - 文本模式：使用 FrontendOrchestrator 处理

**技术要点**：
- WebSocket 实时通信（复用 realtime_dialog_client.py）
- 音频流管理（复用 audio_manager.py）
- 协议封装（复用 protocol.py）
- 可选 AEC（回声消除）支持
- 延迟加载机制（避免 pyaudio 依赖冲突）

**验收**：语音输入→语音输出闭环可用 ✅
- 12/12 测试通过
- 三种模式支持（audio/audio_file/text）
- 工厂方法可用
- 环境检查工具正常

**实施日期**：2025-01-19
**报告**：del_agent/config/project1/result_report/phase4.1_4.2_result.md

#### Step 4.2：双通道入口（文本/语音）✅ 已完成
**文件**：main.py（或 del_agent/main.py）
- 提供两种入口：
  - 文本交互：使用 FrontendOrchestrator（stdin/stdout）
  - 语音交互：使用 voice_adapter（端到端语音对话）
- 模式切换：通过 `--mod` 参数控制（audio/text）

**验收**：两种入口均可独立运行 ✅
- 文本模式正常工作
- 语音模式正常工作
- 命令行参数解析正确
- 用户 ID 管理完善

**实施日期**：2025-01-19
**报告**：del_agent/config/project1/result_report/phase4.1_4.2_result.md

---

### Phase 5：存储与检索接入（Mem0 绑定）✅ 已完成
**目标**：RAG 与知识更新写入 Mem0。

#### Step 5.1：RAG 检索对接 ✅ 已完成
**文件**：storage/vector_store.py（新增）
- 通过 Mem0 实现 search/insert 接口对齐
- VectorStore 类：向量检索、插入、批量操作
- VectorRecord 数据结构：content、score、metadata
- 支持语义搜索和向量存储

**验收**：插入/检索/批量操作可用 ✅
- 10/10 测试通过
- search() 向量检索正常
- insert() 和 batch_insert() 正常
- 与 Mem0 + Qdrant 正确对接

**实施日期**：2026-01-19
**报告**：del_agent/config/project1/result_report/phase5.1_5.2_result.md

#### Step 5.2：知识图谱对接 ✅ 已完成
**文件**：storage/knowledge_graph.py（新增）
- 将 StructuredKnowledgeNode 写入 Mem0 图谱
- KnowledgeGraph 类：节点/关系管理
- NodeType/RelationType 枚举：类型定义
- 支持节点查询、关系查询、聚类查询、路径查找

**验收**：插入/检索/聚类查询可用 ✅
- 16/16 测试通过
- add_node() 和 add_relation() 正常
- query_nodes() 和 query_relations() 正常
- cluster_query() 聚类查询正常
- 与 Mem0 + Neo4j 正确对接

**实施日期**：2026-01-19
**报告**：del_agent/config/project1/result_report/phase5.1_5.2_result.md

---

## 3. 交付物清单
- frontend/user_profile.py
- agents/persona.py
- agents/info_extractor.py
- frontend/orchestrator.py
- frontend/voice_adapter.py
- main.py（或 del_agent/main.py）
- tests所有阶段已完成 ✅
**项目完成度**：100% (Phase 1-5 全部完成)
**下一步**：集成测试与优化
## 4. 测试计划（每步必做）
- 单元测试：每个新模块至少 3 个用例
- 集成测试：
  - 文本端到端（用户输入→回答→抽取→后端→入库）
  - 语音端到端（语音输入→语音输出）

## 5. 执行顺序（最短路径）
1) Step 3.2 用户画像
2) Step 3.3 PersonaAgent
3) Step 3.4 InfoExtractorAgent
4) Step 3.5 Orchestrator 文本闭环
5) Step 4.1 语音适配器
6) Step 4.2 双入口主流程
7) Step 5 Mem0 接入与校验

## 6. 注意事项
- 任何新增模块必须保持与 BaseAgent/LLMProvider 兼容。
- 文本流程优先保证稳定，再接入语音通道。
- 不重复实现向量库/知识图谱，只做接口封装和对接。

---
**状态**：Phase 4 已完成 ✅，进入 Phase 5
**下一步**：Phase 5 Step 5.1 开始（RAG 检索对接）
