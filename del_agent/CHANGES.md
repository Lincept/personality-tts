# 项目更新日志 (Changelog)

## [2.3.0] - 2026-01-19 ✨

### 🎉 Phase 2 后端数据工厂完成

#### 新增智能体
- **WeigherAgent**（权重分析智能体）
  - 基于身份可信度、时间衰减、离群点检测的三维权重算法
  - 支持指数衰减模型（半衰期180天）
  - 完善的离群点检测机制
- **CompressorAgent**（结构化压缩智能体）
  - 支持9种评价维度自动提取
  - 智能内容压缩算法
  - 生成标准化知识节点

#### 新增核心功能
- **DataFactoryPipeline**（数据工厂流水线）
  - 完整的端到端处理流程：RawReview → StructuredKnowledgeNode
  - 支持批量处理
  - 可选的核验循环集成
  - 详细的统计信息和日志追踪

#### 文档和测试
- 新增 `ARCHITECTURE.md` 完整系统架构文档
- 新增 `tests/test_pipeline.py` 流水线测试
- 新增 Phase 2.3-2.5 实施报告

#### 改进
- 更新 README.md，添加流水线使用示例
- 完善项目结构说明
- 更新版本状态和下一步计划

### 技术亮点
- 科学的权重评估算法（可解释性强）
- 智能维度提取（支持9种维度）
- 模块化流水线编排（易于扩展）
- 完善的错误处理和日志系统

### 相关文档
- [Phase 2.3-2.5 实施报告](config/project1/result_report/phase2_3_5_backend_completion.md)
- [系统架构文档](ARCHITECTURE.md)

---

## Del Agent 项目独立化改动说明

## 改动概述

将 `del_agent` 项目从 `src` 目录移出，使其成为独立的工程，并使用 `.env` 文件管理 API 密钥。

## 主要改动

### 1. 路径更新

#### [del_agent/utils/config.py](del_agent/utils/config.py)
- **自动发现配置文件**：ConfigManager 初始化时自动查找 `del_agent/config/settings.yaml`
- **环境变量加载**：优先从 `del_agent/.env` 加载环境变量
- **修复环境变量映射**：正确映射各 LLM 提供者的环境变量名
  - `DOBAO_API_KEY` / `DOBAO_API_SECRET` → doubao
  - `OPENAI_API_KEY` → openai
  - `DEEPSEEK_API_KEY` → deepseek
  - `MOONSHOT_API_KEY` → moonshot
  - `QWEN_API_KEY` → qwen

#### [del_agent/examples/demo.py](del_agent/examples/demo.py)
- 更新路径注释，反映项目已从 `src` 移出
- 变量名从 `src_dir` 改为 `project_root`，更清晰

#### [del_agent/README.md](del_agent/README.md)
- 更新项目结构说明：`src/del_agent/` → `del_agent/`
- 添加 `.env` 配置说明和使用指南
- 更新快速启动步骤

### 2. 新增文件

#### [del_agent/.env.example](del_agent/.env.example)
```bash
# 模板文件，包含所有支持的 LLM API 密钥配置
DOBAO_API_KEY=your_dobao_api_key_here
DOBAO_API_SECRET=your_dobao_api_secret_here
OPENAI_API_KEY=your_openai_api_key_here
# ... 其他提供者
```

#### [del_agent/.gitignore](del_agent/.gitignore)
- 忽略 `.env` 文件，保护密钥安全
- 忽略 Python 缓存、IDE 配置、日志等

#### [del_agent/examples/test_config.py](del_agent/examples/test_config.py)
- 配置测试脚本
- 检查环境变量是否正确加载
- 显示所有 LLM 提供者和智能体配置状态
- 提供友好的错误提示

#### [del_agent/run.sh](del_agent/run.sh)
- 快速启动脚本
- 自动设置 PYTHONPATH
- 自动检查 .env 文件
- 支持 `./run.sh test-config` 和 `./run.sh demo`

## 使用方式

### 1. 配置环境

```bash
cd del_agent
cp .env.example .env
# 编辑 .env，填写真实的 API 密钥
```

### 2. 测试配置

```bash
./run.sh test-config
```

输出示例：
```
=== Del Agent 配置测试 ===

1. 环境变量检查:
   ✓ DOBAO_API_KEY: b7adb98a-0...
   ✓ OPENAI_API_KEY: sk-proj...

2. LLM 提供者配置:
   - doubao: ERNIE-Bot-4 (API Key: 已设置)
   - openai: gpt-3.5-turbo (API Key: 已设置)

✓ 配置正常，可以运行 demo.py
```

### 3. 运行示例

```bash
./run.sh demo
```

## 技术细节

### 环境变量加载顺序

1. `ConfigManager.__init__()` 调用 `load_dotenv(dotenv_path=del_agent/.env)`
2. 从 `.env` 文件加载环境变量到 `os.environ`
3. 加载 `config/settings.yaml` 配置文件
4. `_parse_config()` 中，如果配置文件的 `api_key` 为空，从环境变量读取
5. 使用映射表匹配提供者名称到环境变量名

### 配置优先级

1. 环境变量（`.env` 文件）
2. `config/settings.yaml` 配置文件
3. 代码中的默认值

### 路径解析

所有路径相关逻辑使用 `Path(__file__).resolve().parent` 进行相对路径计算，确保无论从哪里运行都能正确找到配置文件。

## 验证清单

- [x] 从 .env 文件正确加载环境变量
- [x] ConfigManager 自动发现 config/settings.yaml
- [x] PromptManager 自动发现 prompts/templates/
- [x] demo.py 可以正常运行（连接 API 成功）
- [x] 项目结构独立，不依赖 src 目录
- [x] .env 文件被 .gitignore 忽略

## 注意事项

1. **不要提交 .env 文件**：包含敏感信息，已被 .gitignore 忽略
2. **首次使用**：必须从 .env.example 复制并填写真实密钥
3. **多环境**：可以创建 .env.local、.env.dev 等，需在代码中指定
4. **PYTHONPATH**：使用 run.sh 或手动设置 `PYTHONPATH=/path/to/AI-Sandbox`

## 后续优化建议

1. 添加 `setup.py` 或 `pyproject.toml`，支持 `pip install -e .`
2. 支持从命令行参数指定 LLM 提供者
3. 添加更多配置验证和错误提示
4. 考虑使用 `python-dotenv` 的高级特性（如 `.env.local` 覆盖）
