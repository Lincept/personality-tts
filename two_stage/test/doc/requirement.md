请注意：代码实现在src/del_agent中
# Role
你是一个精通 Python 后端架构、LLM 应用开发（Agent Workflow）以及 ETL 数据处理的资深架构师。

# Context
我们要从零开始搭建一个“后端 AI 数据工厂”。
这个系统的核心目标不是聊天，而是静默处理海量的非结构化文本数据（如导师评价、实验室内幕），将其转化为多维度、结构化的知识库。
我们需要一个高扩展性的 Sandbox（沙盒）环境，以便后续进行多智能体（Multi-Agent）协作开发和 Prompt 工程实验。

# Task
请为我初始化一个 Python 工程框架。不要使用庞大的框架（如 LangChain），我们要从轻量级原生代码开始，以保持对逻辑的完全控制。

# Tech Stack
- Models: Pydantic (用于严格的数据结构定义), OpenAI SDK (或兼容接口)
- Utils: python-dotenv, tenacity (用于重试)

# Architectural Requirements (关键)
请按照以下模块设计代码结构：

1. **LLM Adapter Layer (模型适配层)**:
   - 实现一个 `LLMProvider` 抽象基类。
   - 实现一个基于 OpenAI API 格式的通用适配器（这是关键，因为 DeepSeek、Moonshot 等都兼容 OpenAI 格式）。
   - 允许在实例化时配置 `base_url` 和 `api_key`，以便我们可以轻松切换不同的模型服务商。

2. **Prompt Manager (提示词管理)**:
   - 提示词不能硬编码在 Python 函数里。
   - 设计一个机制，支持从 YAML/JSON 文件或专用的 Py 文件中加载结构化的 Prompt 模板（System Prompt + User Prompt）。
   - 支持 Jinja2 风格的变量替换。

3. **Base Agent Structure (智能体基类)**:
   - 定义一个 `BaseAgent` 类。
   - 包含 `think()` 或 `process()` 方法。
   - 包含 `structure_output` 机制，强制 LLM 返回 JSON 格式，并使用 Pydantic 进行校验。

4. **Sandbox Demo (MVP)**:
   - 请基于上述架构，实现一个具体的 Demo Agent：`RawCommentCleaner`（原始评论清洗员）。
   - **输入**: 一段充满情绪和黑话的文本（例如："这老板简直是'学术妲己'，太会画饼了！经费倒是多，但不发给我们。"）。
   - **预期输出**: 一个 Pydantic 对象，包含：
     - `factual_content` (str): 去除情绪后的事实（如：经费充足，津贴发放少）。
     - `emotional_intensity` (float): 0-1 的情绪评分。
     - `keywords` (list): 提取的关键标签。

# Output Format
1. 请先展示推荐的 **项目目录结构** (File Tree)。
2. 然后提供核心文件的 **完整代码实现**。
3. 并在代码中包含详细的注释，解释设计模式。