我将构建一个轻量级但高度可扩展的AI数据工厂框架，包含：

1. **LLM Adapter Layer**: 实现统一接口的模型适配层，支持OpenAI兼容格式
2. **Prompt Manager**: 支持YAML/JSON模板的提示词管理系统
3. **Base Agent Structure**: 定义智能体基类，支持结构化输出
4. **RawCommentCleaner Demo**: 实现评论清洗Agent示例

项目采用模块化设计，使用Pydantic进行数据验证，支持多模型服务商切换，为后续多智能体协作和Prompt工程实验提供沙盒环境。