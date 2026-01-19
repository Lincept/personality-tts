# del_agent 测试使用说明

本目录包含了 del_agent 的各种测试，展示如何像真实用户一样使用该系统。

## 📋 测试文件列表

### 1. `test_complete_pipeline.py` - 完整流水线测试 ⭐
**推荐首先运行此测试**

展示 del_agent 的完整数据工厂流水线，从原始评论到结构化知识节点的端到端处理。

**功能展示:**
- ✓ 批量处理多条评论
- ✓ 完整的四步流水线: 清洗 → 解码 → 权重 → 压缩
- ✓ 统计信息输出
- ✓ 结果保存为 JSON

**运行方式:**
```bash
cd del_agent
python tests/test_complete_pipeline.py
```

**输出示例:**
```
原始评论: "这老板简直是'学术妲己'，太会画饼了！经费倒是多，但津贴不发给我们。"

处理结果:
  导师ID: mentor_unknown
  评价维度: Funding
  事实内容: 经费充足，津贴发放少
  综合权重: 0.400
  标签: 经费, 津贴, 学术妲己, 画饼
```

**结果文件:** 
- 保存在 `output/test_results_YYYYMMDD_HHMMSS.json`

---

### 2. `test_individual_agents.py` - 单个智能体测试

展示如何单独使用每个智能体，适合想了解各个组件功能的开发者。

**包含测试:**
1. **RawCommentCleaner** - 评论清洗
   - 去除情绪化表达
   - 提取客观事实
   - 识别关键词

2. **SlangDecoderAgent** - 黑话解码
   - 识别学术黑话（如"学术妲己"、"画饼"、"放羊"）
   - 翻译为标准表述
   - 维护动态词典

3. **WeigherAgent** - 权重分析
   - 评估信息可信度
   - 考虑身份、时间等因素
   - 检测异常值

4. **CompressorAgent** - 结构化压缩
   - 提取评价维度
   - 生成知识节点
   - 压缩信息

**运行方式:**
```bash
cd del_agent
python tests/test_individual_agents.py
```

---

### 3. `test_simple.py` - 快速测试

简单快速的测试，验证基本功能是否正常。

**运行方式:**
```bash
cd del_agent
python tests/test_simple.py
```

---

## 🚀 快速开始

### 前置条件

1. **安装依赖:**
```bash
pip install -r requirements.txt
```

2. **配置环境变量:**
创建 `.env` 文件，添加 API Key:
```bash
# 豆包模型（推荐）
ARK_API_KEY=your_api_key_here

# 或其他模型
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
```

### 运行推荐流程

```bash
# 1. 进入项目目录
cd del_agent

# 2. 运行完整流水线测试（推荐）
python tests/test_complete_pipeline.py

# 3. 查看结果
cat output/test_results_*.json
```

---

## 📊 测试结果说明

### 完整流水线输出结构

```json
{
  "test_time": "20260119_203636",
  "config": {
    "enable_verification": false,
    "model": "doubao-seed-1-6-251015"
  },
  "results": [
    {
      "review_index": 1,
      "original_content": "原始评论内容",
      "success": true,
      "knowledge_node": {
        "mentor_id": "mentor_unknown",
        "dimension": "Funding",
        "fact_content": "事实内容",
        "weight_score": 0.4,
        "tags": ["标签1", "标签2"]
      }
    }
  ],
  "statistics": {
    "total_processed": 3,
    "successful": 3,
    "failed": 0,
    "success_rate": 1.0
  }
}
```

### 知识节点字段说明

- `mentor_id`: 导师唯一标识
- `dimension`: 评价维度（Funding/Personality/Academic_Geng 等）
- `fact_content`: 去情绪化的事实内容
- `original_nuance`: 保留的原文特色或黑话
- `weight_score`: 综合权重评分 (0-1)
- `tags`: 相关标签列表
- `last_updated`: 最后更新时间

---

## 🔧 自定义测试

### 使用自己的数据

修改 `test_complete_pipeline.py` 中的测试数据：

```python
test_reviews = [
    {
        "content": "你的评论内容",
        "metadata": {
            "platform": "知乎",
            "author_id": "user_001",
            "author_role": "博士生",
            "post_time": "2025-12-01"
        }
    },
    # 添加更多评论...
]
```

### 启用核验循环

修改流水线初始化参数：

```python
pipeline = DataFactoryPipeline(
    llm_provider=llm_provider,
    enable_verification=True,  # 启用核验
    strictness_level=0.7,      # 严格度等级 (0-1)
    max_retries=3              # 最大重试次数
)
```

---

## 📝 评价维度说明

系统支持以下评价维度：

- **Funding**: 经费资助
- **Personality**: 导师性格
- **Academic_Geng**: 学术耿直/严格度
- **Work_Pressure**: 工作压力
- **Lab_Atmosphere**: 实验室氛围
- **Publication**: 发表论文
- **Career_Development**: 职业发展
- **Equipment**: 设备条件
- **Other**: 其他

---

## ❓ 常见问题

### Q: 测试运行失败？
A: 检查：
1. API Key 是否正确配置
2. 网络连接是否正常
3. 依赖包是否完整安装

### Q: 如何切换 LLM 模型？
A: 修改 `OpenAICompatibleProvider` 的参数：
```python
llm_provider = OpenAICompatibleProvider(
    model_name="your-model-name",
    api_key="your-api-key",
    base_url="your-base-url"
)
```

### Q: 处理速度慢？
A: 可以：
1. 关闭核验循环 (`enable_verification=False`)
2. 减少测试数据量
3. 使用更快的模型

---

## 📚 更多文档

- [系统架构](../ARCHITECTURE.md)
- [项目说明](../README.md)
- [需求文档](../config/project1/req1.md)

---

**最后更新:** 2026年1月19日
