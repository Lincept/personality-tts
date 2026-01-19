# backend_main.py 使用指南

后端批量处理工具，用于处理教授评论数据并存储到知识库。

## 快速开始

```bash
cd del_agent

# 处理 5 个文件（默认 JSON 存储）
python backend_main.py process --limit 5

# 查看存储的记录
python backend_main.py show --limit 10

# 查看统计信息
python backend_main.py stats
```

## 命令详解

### 1. process - 批量处理

```bash
python backend_main.py process [选项]
```

| 选项                             | 说明                  |
| -------------------------------- | --------------------- |
| `--limit N, -l N`                | 最大处理文件数量      |
| `--store {json,mem0,hybrid}, -s` | 存储后端（默认 json） |
| `--trace, -t`                    | 启用跟踪输出          |
| `--no-store`                     | 只处理不存储          |
| `--verify`                       | 启用 LLM 核验循环     |
| `--data-dir PATH, -d`            | 数据目录路径          |

**示例：**

```bash
# 处理前 10 个文件，使用 JSON 存储
python backend_main.py process --limit 10

# 使用 Mem0 向量存储（需要 QWEN_API_KEY）
python backend_main.py process --limit 5 --store mem0

# 混合存储（同时写入 JSON 和 Mem0）
python backend_main.py process --limit 5 --store hybrid

# 只处理不存储，带跟踪输出
python backend_main.py process --limit 3 --no-store --trace
```

### 2. show - 展示记录

```bash
python backend_main.py show [选项]
```

| 选项                             | 说明                    |
| -------------------------------- | ----------------------- |
| `--limit N, -l N`                | 返回记录数量（默认 10） |
| `--query TEXT, -q`               | 搜索关键词              |
| `--user-id ID, -u`               | 按教授 SHA1 过滤        |
| `--store {json,mem0,hybrid}, -s` | 存储后端                |

**示例：**

```bash
# 展示前 10 条记录
python backend_main.py show --limit 10

# 搜索包含"学术"的记录
python backend_main.py show --query "学术"

# 使用 Mem0 语义搜索（需指定 user_id）
python backend_main.py show --store mem0 --query "科研经费" --user-id "0006e7cff3c..."
```

### 3. stats - 查看统计

```bash
python backend_main.py stats [--store {json,mem0,hybrid}]
```

**输出示例：**

```
========================================
知识存储统计信息
========================================
  存储后端: json
  存储路径: /path/to/del_agent/data/knowledge_store
  总记录数: 11

  按维度统计:
    Academic_Geng: 3
    Funding: 7
    Career_Development: 1

  按用户/教授统计: 3 个分组
========================================
```

## 存储后端

| 后端       | 特点                 | 依赖         |
| ---------- | -------------------- | ------------ |
| **json**   | 本地文件，关键词搜索 | 无           |
| **mem0**   | 向量语义搜索         | QWEN_API_KEY |
| **hybrid** | 双写，优先语义搜索   | QWEN_API_KEY |

### 如何选择存储后端

使用 `--store` 或 `-s` 参数指定存储后端：

```bash
# 使用 JSON 存储（默认）
python backend_main.py process --limit 5 --store json

# 使用 Mem0 向量存储
python backend_main.py process --limit 5 --store mem0

# 使用混合存储
python backend_main.py process --limit 5 --store hybrid
```

**选择建议：**

| 场景            | 推荐后端 | 原因                |
| --------------- | -------- | ------------------- |
| 快速测试/开发   | `json`   | 无需 API，速度快    |
| 需要语义搜索    | `mem0`   | 支持向量相似度搜索  |
| 生产环境        | `hybrid` | 双重保障，语义+备份 |
| 无 QWEN_API_KEY | `json`   | 唯一可用选项        |

### 查看不同存储库的数据

**关键：使用相同的 `--store` 参数来读取对应存储库**

```bash
# 查看 JSON 存储的记录
python backend_main.py show --store json --limit 10
python backend_main.py stats --store json

# 查看 Mem0 存储的记录（需要指定 user_id 进行搜索）
python backend_main.py show --store mem0 --query "学术" --user-id "0006e7cff3c..."
python backend_main.py stats --store mem0

# 查看混合存储的统计（显示两个存储库的信息）
python backend_main.py stats --store hybrid
```

**注意事项：**

1. **JSON 存储**：支持 `get_all` 获取所有记录，支持关键词搜索
2. **Mem0 存储**：必须指定 `--user-id` 和 `--query` 进行搜索，不支持列出所有记录
3. **Hybrid 存储**：`show` 从 JSON 获取，`search` 优先使用 Mem0 语义搜索

### 存储位置

- **JSON**: `data/knowledge_store/`
  ```
  data/knowledge_store/
  ├── index.json          # 索引文件
  └── records/
      └── {sha1}/         # 按教授分组
          └── {id}.json   # 知识记录
  ```

- **Mem0/Qdrant**: `data/qdrant/`
  ```
  data/qdrant/
  └── collection/         # Qdrant 向量数据库文件
  ```

## 环境变量

在 `.env` 文件中配置：

```bash
# LLM API Key（处理必需）
ARK_API_KEY=xxx          # 豆包 API

# Mem0 存储（可选）
QWEN_API_KEY=xxx         # 通义千问 API（用于 embedding）

# 调试开关
BACKEND_TRACE_ENABLED=true   # 跟踪输出
BACKEND_VERBOSE=true         # 详细日志
```

## 数据流程

```
data/professors/*.json
        ↓
    解析评论
        ↓
  DataFactoryPipeline
  (Cleaner → Decoder → Weigher → Compressor)
        ↓
  StructuredKnowledgeNode
        ↓
  KnowledgeStore (json/mem0/hybrid)
```

## 常用场景

```bash
# 1. 快速测试（不存储）
python backend_main.py process --limit 1 --no-store --trace

# 2. 小批量处理并查看
python backend_main.py process --limit 5
python backend_main.py show --limit 20

# 3. 启用语义搜索
python backend_main.py process --limit 10 --store mem0
python backend_main.py show --store mem0 --query "导师人品"

# 4. 查看处理统计
python backend_main.py stats --store hybrid
```
