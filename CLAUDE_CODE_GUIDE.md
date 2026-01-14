# Claude Code 使用指南 - Token 优化

本指南帮助你高效使用 Claude Code，减少 token 消耗，提高响应速度。

## 📋 目录

- [快速开始](#快速开始)
- [Token 优化策略](#token-优化策略)
- [最佳实践](#最佳实践)
- [常见任务示例](#常见任务示例)
- [故障排除](#故障排除)

---

## 🚀 快速开始

### 1. 项目配置

本项目已配置以下文件来优化 token 使用：

- **`.claudeignore`** - 排除不必要的文件（类似 `.gitignore`）
- **`.claude/config.json`** - Claude Code 配置和最佳实践

### 2. 基本原则

✅ **DO（推荐）**：
- 使用 `.claudeignore` 排除大文件
- 使用 `Grep` 搜索代码
- 使用 `Glob` 查找文件
- 使用 `Task` tool 处理复杂任务
- 一次只关注一个任务

❌ **DON'T（避免）**：
- 读取整个大文件
- 重复读取同一文件
- 在主对话中进行大量文件操作
- 同时处理多个不相关的任务

---

## 💡 Token 优化策略

### 策略 1：使用 .claudeignore

`.claudeignore` 文件会自动排除不必要的文件，减少上下文大小。

**已排除的内容**：
- Python 缓存（`__pycache__/`, `*.pyc`）
- 虚拟环境（`venv/`, `.venv/`）
- 数据文件（`*.mp3`, `*.wav`, `data/`）
- 日志文件（`*.log`）
- 二进制库（`*.dylib`, `*.dll`）
- IDE 配置（`.vscode/`, `.idea/`）

**自定义排除**：
编辑 `.claudeignore` 文件，添加你想排除的文件或目录。

### 策略 2：使用正确的工具

| 任务 | ❌ 低效方式 | ✅ 高效方式 |
|------|-----------|-----------|
| 搜索代码 | `Read` 所有文件 | `Grep` 搜索关键词 |
| 查找文件 | `Bash ls -R` | `Glob` 使用模式匹配 |
| 探索代码 | 读取多个文件 | `Task` + `Explore` agent |
| 规划任务 | 在主对话中讨论 | `EnterPlanMode` |

### 策略 3：限制读取范围

**读取大文件时使用 limit 和 offset**：
```
只读取前 100 行：
Read file_path limit=100

跳过前 50 行，读取接下来的 100 行：
Read file_path offset=50 limit=100
```

**使用 Grep 的 head_limit**：
```
只显示前 10 个匹配：
Grep pattern="function_name" head_limit=10
```

### 策略 4：使用 Agent

对于复杂任务，使用专门的 agent 可以显著减少主对话的 token 消耗。

**Explore Agent**（探索代码）：
```
用于：理解代码结构、查找功能实现
示例："帮我探索 ASR 模块的实现"
```

**Plan Agent**（规划任务）：
```
用于：设计实现方案、架构决策
示例："帮我规划如何添加新的 TTS 提供商"
```

---

## 📚 最佳实践

### 1. 提问技巧

**❌ 模糊的问题**：
```
"帮我看看这个项目"
"有什么问题吗？"
"优化一下代码"
```

**✅ 具体的问题**：
```
"检查 src/asr/audio_input.py 中的 AEC 配置"
"为什么 voice_to_voice.py:127 会报错？"
"优化 AEC 处理器的流延迟设置"
```

### 2. 文件操作

**❌ 低效方式**：
```python
# 读取所有 Python 文件来查找函数
Read src/asr/audio_input.py
Read src/asr/aec_processor.py
Read src/asr/dashscope_asr.py
...
```

**✅ 高效方式**：
```python
# 使用 Grep 搜索函数
Grep pattern="def process_audio" path="src/asr/"
```

### 3. 探索代码

**❌ 低效方式**：
```
读取多个文件来理解项目结构
```

**✅ 高效方式**：
```
使用 Explore agent：
"帮我探索 TTS 模块的实现，thoroughness=quick"
```

### 4. 修改代码

**❌ 低效方式**：
```
1. Read 整个文件
2. 分析代码
3. Edit 修改
```

**✅ 高效方式**：
```
1. Grep 找到需要修改的位置
2. Read 只读取相关部分（使用 limit/offset）
3. Edit 精确修改
```

---

## 🎯 常见任务示例

### 任务 1：查找并修改配置

**场景**：修改 AEC 的流延迟设置

**❌ 低效方式**：
```
1. "帮我看看 AEC 配置"
2. Read src/asr/aec_processor.py（读取整个文件）
3. "修改流延迟为 40ms"
```

**✅ 高效方式**：
```
1. "在 src/asr/aec_processor.py 中搜索 set_stream_delay_ms"
2. Grep pattern="set_stream_delay_ms" path="src/asr/aec_processor.py"
3. "修改第 127 行的流延迟为 40ms"
4. Edit（精确修改）
```

### 任务 2：理解模块功能

**场景**：理解 ASR 模块的工作原理

**❌ 低效方式**：
```
"读取 src/asr/ 下的所有文件"
```

**✅ 高效方式**：
```
"使用 Explore agent 探索 ASR 模块，thoroughness=medium"
```

### 任务 3：添加新功能

**场景**：添加新的 TTS 提供商

**❌ 低效方式**：
```
在主对话中讨论实现细节
```

**✅ 高效方式**：
```
1. "我想添加新的 TTS 提供商"
2. EnterPlanMode（进入规划模式）
3. 在规划模式中设计方案
4. ExitPlanMode（获得批准后实施）
```

### 任务 4：调试错误

**场景**：修复运行时错误

**❌ 低效方式**：
```
"帮我看看为什么程序报错"
```

**✅ 高效方式**：
```
1. "搜索错误信息：AttributeError: 'NoneType' object has no attribute 'process'"
2. Grep pattern="AttributeError" path="."
3. "检查 voice_to_voice.py:184 的 aec_processor 初始化"
4. Read voice_to_voice.py offset=180 limit=20
5. 提供修复方案
```

---

## 🔍 Token 使用监控

### 查看当前 Token 使用

Claude Code 会在每次响应后显示 token 使用情况：

```
Token usage: 5000/200000; 195000 remaining
```

### Token 消耗分析

**高消耗操作**（避免）：
- 读取大文件（>1000 行）
- 读取二进制文件
- 读取多个文件
- 重复读取同一文件

**低消耗操作**（推荐）：
- 使用 Grep 搜索
- 使用 Glob 查找
- 使用 Agent 处理复杂任务
- 精确的 Edit 操作

---

## 🛠️ 故障排除

### 问题 1：Token 消耗过快

**症状**：
- 对话进行到一半就接近 token 限制
- 响应速度变慢

**解决方案**：
1. 检查 `.claudeignore` 是否正确配置
2. 避免读取大文件
3. 使用 Agent 处理复杂任务
4. 一次只关注一个任务
5. 必要时开始新对话

### 问题 2：找不到文件

**症状**：
- Claude 说找不到某个文件
- 文件明明存在

**解决方案**：
1. 检查文件是否在 `.claudeignore` 中
2. 提供完整的文件路径
3. 使用 Glob 确认文件存在

### 问题 3：响应不够详细

**症状**：
- Claude 的回答太简短
- 没有提供足够的上下文

**解决方案**：
1. 提供更具体的问题
2. 明确说明需要什么信息
3. 提供相关的文件路径

---

## 📊 效率对比

### 示例：查找函数定义

| 方法 | Token 消耗 | 时间 | 准确性 |
|------|-----------|------|--------|
| Read 所有文件 | ~50,000 | 慢 | 高 |
| Grep 搜索 | ~1,000 | 快 | 高 |
| Explore agent | ~5,000 | 中 | 高 |

### 示例：修改配置

| 方法 | Token 消耗 | 步骤 |
|------|-----------|------|
| Read + Edit | ~10,000 | 3 步 |
| Grep + Edit | ~2,000 | 2 步 |

---

## 💡 高级技巧

### 1. 批量操作

**场景**：需要修改多个文件

**技巧**：
```
1. 使用 Grep 找到所有需要修改的位置
2. 一次性说明所有修改
3. Claude 会并行处理
```

### 2. 增量探索

**场景**：理解大型项目

**技巧**：
```
1. 先探索高层结构（Explore agent, thoroughness=quick）
2. 再深入具体模块（Explore agent, thoroughness=medium）
3. 最后查看具体实现（Grep + Read）
```

### 3. 上下文管理

**场景**：长时间对话

**技巧**：
```
1. 定期总结当前进度
2. 明确下一步目标
3. 必要时开始新对话
```

---

## 📝 快速参考

### 常用命令

```bash
# 搜索代码
Grep pattern="function_name" path="src/"

# 查找文件
Glob pattern="**/*.py"

# 读取文件（限制行数）
Read file_path limit=100

# 探索代码
Task subagent_type=Explore prompt="探索 ASR 模块"

# 规划任务
EnterPlanMode
```

### .claudeignore 语法

```
# 注释
*.pyc           # 排除所有 .pyc 文件
__pycache__/    # 排除目录
!important.py   # 不排除（即使匹配其他规则）
```

---

## 🔗 相关资源

- [Claude Code 官方文档](https://docs.anthropic.com/en/docs/build-with-claude/claude-code)
- [Claude API 文档](https://docs.anthropic.com/en/api)
- [项目 README](README.md)

---

## 🎉 总结

**核心原则**：
1. ✅ 使用 `.claudeignore` 排除不必要的文件
2. ✅ 使用正确的工具（Grep > Read, Glob > ls）
3. ✅ 使用 Agent 处理复杂任务
4. ✅ 提供具体、明确的问题
5. ✅ 一次只关注一个任务

**预期效果**：
- Token 消耗减少 **50-70%**
- 响应速度提升 **2-3 倍**
- 更精确的结果
- 更流畅的对话体验

---

如有问题，请参考 `.claude/config.json` 中的配置和示例。
