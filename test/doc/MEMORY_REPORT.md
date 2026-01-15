# personality-tts：Memory（长期记忆）使用与开发情况报告

> 本报告基于仓库当前代码实现梳理（截至 2026-01-15）。重点覆盖：当前 memory 的“怎么用”、数据如何落盘、以及后续如何开发/扩展。

## 1. TL;DR（你现在拥有什么）

- 项目有两条“长期记忆”路径：
  - **两阶段记忆对话（推荐/当前主用）**：先用 LLM 分析“要不要检索/要不要存储”，再带着检索结果生成最终回复（见 [src/memory/memory_chat.py](src/memory/memory_chat.py)）。
  - **Prompt 自动检索（备用/可选）**：在构造 system prompt 时按用户输入做一次相关记忆检索并拼进 prompt（见 [src/voice_assistant_prompt.py](src/voice_assistant_prompt.py)）。
- 长期记忆底座是 **mem0ai + Qdrant 本地向量库持久化**：默认写到 `./data/qdrant`，collection 为 `personality_tts_memory`（见 [src/memory/mem0_manager.py](src/memory/mem0_manager.py)）。
- 可选启用 **Neo4j 知识图谱**（relationship 类记忆）但默认关闭（见 [src/memory/mem0_manager.py](src/memory/mem0_manager.py)）。

## 2. 相关模块与职责（代码导航）

### 2.1 Mem0Manager：长期记忆统一封装

文件：[src/memory/mem0_manager.py](src/memory/mem0_manager.py)

职责：
- 初始化 mem0 Memory（LLM + embedding + vector store + 可选 graph store）。
- 提供对外接口：
  - `search_memories(query, user_id, limit)`：检索相关记忆并格式化为 `- ...` 列表字符串。
  - `add_conversation(user_input, assistant_response, user_id)`：保存一轮对话（以 messages 形式）。
  - `get_all_memories(user_id)` / `clear_memories(user_id)`：查看/清空。
  - `close()`：尽量关闭底层 Qdrant client，帮助落盘。

存储配置（关键点）：
- vector store：Qdrant 本地路径 `./data/qdrant`，`on_disk=True`，embedding dim=1024。
- embedder：OpenAI 兼容 provider，模型写死为 `text-embedding-v3`（并指定 `embedding_dims=1024`）。

### 2.2 MemoryEnhancedChat：两阶段“检索/存储决策 + 回复生成”

文件：[src/memory/memory_chat.py](src/memory/memory_chat.py)

职责：
- **第一阶段**：用结构化 JSON 输出判断：
  - `need_memory_search` 是否需要检索
  - `memory_search_query` 语义化检索词
  - `should_save_memory` 是否需要存储
  - `memory_to_save`（fact/relationship + content）
- **存储 Hook**：若第一阶段判定要存储，则调用 mem0 保存（并尝试 flush）。
- **第二阶段**：把“检索到的记忆”作为已知用户信息，生成最终回复。
- 同时支持：
  - `chat()` 非流式
  - `chat_stream()` 流式（为实时 TTS 播放优化）

优点：
- 检索词是“语义化”而不是复述原话，有利于命中向量记忆。
- 不会对所有输入都做检索/存储，减少开销与噪声。

### 2.3 VoiceAssistantPrompt：Prompt 拼装与短期历史

文件：[src/voice_assistant_prompt.py](src/voice_assistant_prompt.py)

职责：
- 角色 prompt、用户信息、知识库、短期对话历史（默认最多 10 轮）。
- 可选：如果传入 `mem0_manager` 且提供 `user_id`，会在 `get_messages()` 内自动调用 `mem0_manager.search_memories()` 把“相关记忆”拼入 system prompt。

注意：当前主流程里，这个类主要用于**短期对话历史管理**，长期记忆更倾向走 `MemoryEnhancedChat`。

### 2.4 LLMClient：工具调用（Function Calling）基础设施

文件：[src/llm/llm_client.py](src/llm/llm_client.py)

职责：
- 提供 `chat_stream_with_tools()`：支持 tools 定义 + tool_executor（自动执行工具后继续对话）。

这为“让 LLM 主动调用 save/search memory 工具”的路线提供了基础能力。

### 2.5 Memory 工具层（目前偏“可用但未完全接入主流程”）

有两套工具封装：

1) 纯函数式工具（更贴近 mem0 官方 cookbook）：[src/memory/memory_tools.py](src/memory/memory_tools.py)
- `initialize_memory_tools(mem0_manager, user_id, verbose)`：初始化全局 mem0_client。
- `get_tool_definitions()`：返回 tools（按是否启用 graph 决定是否包含 `save_relationship`）。
- `execute_tool(name, args)`：执行工具。

2) 面向对象工具封装：[src/memory/mem0_tools.py](src/memory/mem0_tools.py)
- `Mem0Tools.get_tool_definitions()` / `Mem0Tools.execute_tool()`
- `create_memory_tools(mem0_manager, user_id)`

目前仓库中这两套工具层未看到被主入口直接调用（更像为未来接入/实验保留）。

## 3. 运行时如何“用”长期记忆

### 3.1 开启/关闭 memory

项目通过环境变量 + ConfigLoader 合并配置（见 [src/config_loader.py](src/config_loader.py)）。

关键环境变量：
- `ENABLE_MEM0=true|false`：是否启用 mem0（长期记忆总开关）
- `MEM0_USER_ID=...` 或 `DEFAULT_USER_ID=...`：当前用户 id（用于多用户隔离）
- `ENABLE_GRAPH=true|false`：是否启用 Neo4j 图谱
- `NEO4J_URL` / `NEO4J_USERNAME` / `NEO4J_PASSWORD`

建议同时准备 LLM 相关变量（供 LLM 与 mem0 使用）：
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

重要提示（实现细节）：
- `Mem0Manager` 期望从 `mem0` 配置段里拿到 `llm_api_key/llm_base_url/llm_model`。
- 当前 `ConfigLoader` 会把 `.env` 中的 `MEM0_LLM_*` 映射到 `mem0.llm_*`，并在缺省时自动回退使用 `OPENAI_*`。

推荐的做法（在 `.env` 中显式补齐 mem0 配置）：

```bash
# LLM
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen3-max

# Mem0
ENABLE_MEM0=true
MEM0_USER_ID=your_user
ENABLE_GRAPH=false

# Mem0 使用同一套 OpenAI 兼容配置（ConfigLoader 会映射到 mem0.llm_*）
MEM0_LLM_API_KEY=sk-xxx
MEM0_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MEM0_LLM_MODEL=qwen3-max
```

> `MEM0_LLM_*` 目前已被 `ConfigLoader` 支持；如果不设置会自动回退到 `OPENAI_*`。

### 3.2 数据落盘位置（Qdrant）

- Qdrant 本地持久化目录：`data/qdrant/`
- collection：`personality_tts_memory`

仓库中已存在 `data/qdrant/collection/personality_tts_memory/`，说明默认路径就是把向量库放在项目目录下，便于本地开发与复现。

### 3.3 交互侧的“记忆命令”

文字对话入口：[text_to_speech.py](text_to_speech.py)

交互命令实现集中在主交互类里（见 [src/main.py](src/main.py)）：
- `/memories`：查看当前 `user_id` 下的所有长期记忆
- `/clearmem`：清空当前 `user_id` 的长期记忆
- `/user <ID>`：切换 user id（多用户隔离）

## 4. 当前 memory 的“工作流”（两阶段方案）

两阶段 memory 的关键在于把“要不要查/要不要存”的决策从主对话里拆出去，使得：
- 存储更精确（只存值得存的）
- 检索更相关（用语义化 query）
- 主回复更自然（记忆作为背景信息融入，而非硬复述）

建议把它理解为：

```text
用户输入
  ├─ 第一阶段：分析（JSON）
  │    ├─ need_search? → search(query)
  │    └─ should_save? → save(memory)
  └─ 第二阶段：回复生成（带 retrieved_memories）
```

其中分析规则与“语义化检索词生成规则”写死在 [src/memory/memory_chat.py](src/memory/memory_chat.py) 的 system prompt 中，是你最重要的可调参数之一。

## 5. 开发与扩展：你可以改哪里

### 5.1 调整“什么时候存/什么时候搜”

- 修改第一阶段分析 prompt（`ANALYSIS_SYSTEM_PROMPT`）即可：
  - 增加/减少可存储的信息类型（例如加入“用户长期计划/待办”）
  - 调整 relationship vs fact 的判定
  - 强化“不要存”的规则以减少噪声

### 5.2 调整检索策略

可调项：
- `limit`：返回多少条记忆
- `threshold`：相似度阈值（在 `memory_tools.search_memories` 中目前用到，`memory_chat` 路线未显式设置 threshold）
- 查询词生成：决定命中率与准确性（通常比调阈值更关键）

### 5.3 调整写入内容格式与元数据

当前写入通常会加前缀：`User memory - ...`。

可扩展方向：
- 对不同类别写入不同模板（偏好/职业/关系/长期目标），让记忆更结构化。
- 增加 metadata（例如 category、时间戳、来源模块、置信度），便于后续筛选与治理。

### 5.4 接入“工具调用式记忆”（Function Calling 路线）

如果你想让主 LLM 在对话中主动调用：
- `save_memories` / `search_memories` / `save_relationship`

可以把：
- tools：来自 [src/memory/memory_tools.py](src/memory/memory_tools.py)
- 执行器：`execute_tool()`
- LLM 流：`LLMClient.chat_stream_with_tools()`
- 实时播放：用 [src/realtime_pipeline_with_tools.py](src/realtime_pipeline_with_tools.py)

拼起来。

这条路线的优势：
- 不需要额外“第一阶段分析”，由同一个对话模型自己决定何时调用工具。

劣势/注意：
- 需要更强的 prompt 约束，否则工具调用容易过度或遗漏。
- 更容易出现“工具调用循环”，需要合理设置 `max_tool_calls`。

### 5.5 图谱（Neo4j）扩展点

- `Mem0Manager` 内已经支持 graph_store 配置（provider=neo4j）。
- `memory_tools.get_tool_definitions()` 会在启用图谱时暴露 `save_relationship`。

建议在启用图谱前先确认：
- Neo4j 是否可用、网络连通、认证正确
- 你确实需要关系推理/关系查询，否则先用纯向量存储更简单

## 6. 调试与测试

### 6.1 单元/集成测试入口

- 两阶段对话测试脚本：[test_memory_chat.py](test_memory_chat.py)
  - 覆盖：自我介绍触发存储、询问记忆触发检索、闲聊不触发、分享偏好触发存储等。

### 6.2 日志

- `MemoryEnhancedChat` 使用 logger 名称 `memory_chat`。
- 测试脚本会输出到 `logs/memory_chat.log`。
- 主程序支持 `PTTS_LOG_LEVEL` 控制日志级别（见 [src/main.py](src/main.py)）。

### 6.3 数据持久化与退出

- Qdrant 本地持久化依赖 `on_disk=True`。
- `Mem0Manager.close()` 尝试关闭底层 client 来触发持久化（尽量保障退出时落盘）。
- 交互退出（Ctrl+C）时，主程序会调用 `mem0_manager.close()`。

## 7. 已知风险与建议

- 配置一致性：
  - 当前 mem0 初始化依赖 `mem0.llm_*`；`ConfigLoader` 会把 `MEM0_LLM_*` 映射到这些字段，并在缺省时回退使用 `OPENAI_*`。
  - 如果既没设置 `MEM0_LLM_*` 也没设置 `OPENAI_*`，那么开启 `ENABLE_MEM0=true` 仍可能导致 mem0 初始化失败（缺少鉴权/模型信息）。
- 隐私与合规：
  - 长期记忆会把用户偏好/身份信息写入本地库；如果要上线/共享机器，请明确用户告知与数据清理机制。
- 记忆污染：
  - 如果存储 prompt 规则过宽，容易把噪声写进向量库，导致检索误导。建议严格定义“值得存”的边界。
- 成本与时延：
  - 两阶段方案每轮至少两次 LLM 调用（分析+回复），需要注意吞吐与费用。可以对“闲聊/短输入”直接跳过第一阶段或做缓存。

---

## 附：关键文件索引

- Memory 核心：
  - [src/memory/mem0_manager.py](src/memory/mem0_manager.py)
  - [src/memory/memory_chat.py](src/memory/memory_chat.py)
- Prompt（含可选自动检索）：
  - [src/voice_assistant_prompt.py](src/voice_assistant_prompt.py)
- 工具调用（可扩展路线）：
  - [src/memory/memory_tools.py](src/memory/memory_tools.py)
  - [src/memory/mem0_tools.py](src/memory/mem0_tools.py)
  - [src/llm/llm_client.py](src/llm/llm_client.py)
  - [src/realtime_pipeline_with_tools.py](src/realtime_pipeline_with_tools.py)
- 使用入口：
  - [text_to_speech.py](text_to_speech.py)
  - [voice_to_voice.py](voice_to_voice.py)
- 测试：
  - [test_memory_chat.py](test_memory_chat.py)
