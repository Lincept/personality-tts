# Pipeline 性能计时功能

## 概述

Pipeline 现在会自动记录每条评论处理的详细耗时信息，包括每个步骤的执行时间和占比。

## 功能特性

### 自动计时
- ✅ 每个处理步骤的独立计时
- ✅ 总处理时间统计
- ✅ 各步骤耗时占比分析
- ✅ 详细的日志输出

### 计时步骤

Pipeline 分为 4 个主要步骤：

1. **Step 1 (Cleaning)**: 评论清洗
   - 去除情绪化表达
   - 提取事实内容
   - 关键词提取

2. **Step 2 (Decoding)**: 黑话解码
   - 识别网络用语
   - 行业术语翻译
   - 词典动态更新

3. **Step 3 (Weighing)**: 权重计算
   - 信息可信度评估
   - 时间衰减计算
   - 综合权重评分

4. **Step 4 (Compression)**: 结构化压缩
   - 维度分类
   - 信息提取
   - 知识节点生成

## 日志输出示例

```log
2026-01-19 20:23:23,529 - backend.factory - INFO - ✓ Cleaned in 2.81s: 经费充足但津贴发放少...
2026-01-19 20:23:25,429 - backend.factory - INFO - ✓ Decoded in 1.90s: 0 slang terms found
2026-01-19 20:23:25,429 - backend.factory - INFO - ✓ Weight analyzed in 0.00s: score=0.40
2026-01-19 20:23:25,430 - backend.factory - INFO - ✓ Compressed in 0.00s: dimension=Funding
2026-01-19 20:23:25,430 - backend.factory - INFO - ✅ Pipeline completed successfully in 4.71s
   ├─ Step 1 (Cleaning):    2.81s (59.6%)
   ├─ Step 2 (Decoding):    1.90s (40.4%)
   ├─ Step 3 (Weighing):    0.00s (0.0%)
   └─ Step 4 (Compression): 0.00s (0.0%)
   Result: Mentor=mentor_unknown | Dimension=Funding | Weight=0.40
```

## 使用方法

### 1. 运行性能测试

```bash
# 设置环境变量
export PYTHONPATH=/path/to/del_agent:$PYTHONPATH

# 运行测试
python tests/test_timing.py
```

### 2. 在代码中使用

```python
from backend.factory import DataFactoryPipeline
from models.schemas import RawReview
from core.llm_adapter import OpenAICompatibleProvider

# 创建 LLM Provider
llm_provider = OpenAICompatibleProvider(...)

# 创建 Pipeline
pipeline = DataFactoryPipeline(llm_provider)

# 处理评论 - 自动记录耗时
result = pipeline.process_raw_review(raw_review)

# 查看日志中的性能统计
```

### 3. 批量处理性能分析

```bash
# 运行完整测试（包含5条评论）
python tests/test_doubao.py
```

输出会显示每条评论的详细处理时间。

## 性能优化建议

根据计时数据，可以针对性地优化：

### 如果 Cleaning 步骤耗时较长 (>3s)
- 检查 prompt 复杂度
- 考虑使用更快的模型
- 调整 `reasoning_effort` 参数

### 如果 Decoding 步骤耗时较长 (>2s)
- 检查黑话词典大小
- 优化词典查询逻辑
- 考虑缓存机制

### 如果 Weighing 步骤耗时较长
- 简化权重计算逻辑
- 使用本地计算替代 LLM 调用

### 如果 Compression 步骤耗时较长
- 优化数据结构
- 减少字段处理复杂度

## 相关文件

- `backend/factory.py` - Pipeline 主逻辑和计时实现
- `tests/test_timing.py` - 性能计时测试脚本
- `tests/test_doubao.py` - 完整功能测试（包含性能统计）

## 技术实现

计时功能使用 Python 的 `datetime` 模块：

```python
step1_start = datetime.now()
# ... 执行步骤 1
step_timings["step1_cleaning"] = (datetime.now() - step1_start).total_seconds()
```

所有计时数据都会记录到日志中，便于性能分析和调优。
