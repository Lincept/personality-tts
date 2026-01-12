# 导师评价网站 - Agent 设计文档

## 1. 核心机制：表单填充系统

### 1.1 表单结构

Agent 维护一个内部表单，用于收集用户信息：

```json
{
  "user_form": {
    "school": null,           // 学校名称（必填）
    "major": null,            // 专业名称（必填）
    "research_direction": null,  // 研究方向（可选）
    "preferences": {
      "personality": null,    // 导师性格偏好（可选）
      "research_style": null, // 研究风格偏好（可选）
      "funding": null         // 经费情况偏好（可选）
    }
  },
  "form_status": {
    "is_complete": false,     // 表单是否完整（school + major 都有）
    "missing_required": ["school", "major"],  // 缺失的必填项
    "filled_optional": []     // 已填写的可选项
  }
}
```

### 1.2 填表机制

#### 信息提取流程

```
用户输入（自然语言）
    ↓
LLM 提取结构化信息
    ↓
更新表单字段
    ↓
检查表单完整性
    ↓
触发相应动作
```

#### 提取规则

1. **学校提取**
   - 识别关键词：大学、学院、XX大
   - 标准化：北京大学、清华大学、中国科学院大学
   - 模糊匹配：北大 → 北京大学

2. **专业提取**
   - 识别关键词：系、专业、学科
   - 标准化：计算机科学与技术、电子信息工程
   - 模糊匹配：计算机 → 计算机科学与技术

3. **研究方向提取**
   - 识别关键词：方向、领域、研究
   - 示例：机器学习、深度学习、计算机视觉

4. **偏好提取**
   - 性格：温和、严格、放养、负责
   - 风格：理论型、工程型、产业型
   - 经费：充足、一般、紧张

### 1.3 触发机制

#### 触发条件

```python
# 触发排行榜更新的条件
if form["school"] is not None and form["major"] is not None:
    trigger_update_ranking()
```

#### 触发时机

1. **排行榜更新**
   - 条件：school + major 都填写
   - 动作：调用 `update_ranking(school, major)`
   - 反馈：语音告知 + 页面更新

2. **导师推荐**
   - 条件：school + major + 至少一个偏好
   - 动作：调用 `recommend_advisors(form)`
   - 反馈：语音介绍推荐理由

3. **导师详情**
   - 条件：用户明确选择某位导师
   - 动作：调用 `get_advisor_detail(advisor_id)`
   - 反馈：跳转详情页

### 1.4 提示机制

#### 缺失必填项提示

```
场景 1：只有学校，没有专业
Agent: "好的，北京大学。你想考哪个专业呢？"

场景 2：只有专业，没有学校
Agent: "计算机专业，请问是哪个学校的呢？"

场景 3：都没有
Agent: "你好！我是导师推荐助手。请告诉我你想考哪个学校的哪个专业？"
```

#### 可选项引导

```
场景：必填项已完成，引导填写可选项
Agent: "已经为你筛选出北大计算机系的导师。你对研究方向或导师风格有偏好吗？"
```

---

## 2. LLM 输出格式

### 2.1 输出结构

LLM 的每次输出包含两部分：

```json
{
  "voice_response": "好的，北京大学计算机系。正在为你筛选导师...",
  "tool_calls": [
    {
      "tool": "update_form",
      "params": {
        "school": "北京大学",
        "major": "计算机科学与技术"
      }
    },
    {
      "tool": "update_ranking",
      "params": {
        "school": "北京大学",
        "major": "计算机科学与技术"
      }
    }
  ]
}
```

### 2.2 语音回复（voice_response）

#### 设计原则

1. **简洁**：2-3 句话，最多 50 字
2. **口语化**：自然流畅，适合 TTS
3. **反馈明确**：告知用户发生了什么
4. **引导性**：提示下一步可以做什么

#### 回复模板

```
信息确认：
"好的，{school}{major}。正在为你筛选导师..."

缺失信息：
"请问你想考哪个学校的哪个专业呢？"

推荐导师：
"根据你的需求，我推荐{导师名}教授，他主要研究{方向}。"

导师详情：
"这是{导师名}的详细信息，你可以看看他的研究方向和学生评价。"
```

### 2.3 工具调用（tool_calls）

#### 可用工具列表

1. **update_form** - 更新表单
   ```json
   {
     "tool": "update_form",
     "params": {
       "school": "北京大学",
       "major": "计算机科学与技术",
       "research_direction": "机器学习",
       "preferences": {
         "personality": "温和"
       }
     }
   }
   ```

2. **update_ranking** - 更新排行榜
   ```json
   {
     "tool": "update_ranking",
     "params": {
       "school": "北京大学",
       "major": "计算机科学与技术"
     }
   }
   ```

3. **recommend_advisors** - 推荐导师
   ```json
   {
     "tool": "recommend_advisors",
     "params": {
       "school": "北京大学",
       "major": "计算机科学与技术",
       "preferences": {
         "research_direction": "机器学习",
         "personality": "温和"
       }
     }
   }
   ```

4. **get_advisor_detail** - 获取导师详情
   ```json
   {
     "tool": "get_advisor_detail",
     "params": {
       "advisor_id": "12345",
       "advisor_name": "张三"
     }
   }
   ```

---

## 3. 页面感知机制

### 3.1 页面状态输入

Agent 能够接收页面的当前状态：

```json
{
  "page_context": {
    "current_page": "ranking",  // 当前页面：ranking/detail/home
    "visible_advisors": [       // 当前可见的导师列表
      {
        "id": "12345",
        "name": "张三",
        "title": "教授",
        "rating": 4.5,
        "rank": 1
      },
      {
        "id": "12346",
        "name": "李四",
        "title": "副教授",
        "rating": 4.3,
        "rank": 2
      }
    ],
    "selected_advisor": null,   // 用户当前选中的导师
    "ranking_filters": {        // 当前排行榜的筛选条件
      "school": "北京大学",
      "major": "计算机科学与技术"
    }
  }
}
```

### 3.2 页面感知能力

#### 能力 1：识别用户指代

```
用户："第一个导师怎么样？"
Agent 处理：
1. 读取 page_context.visible_advisors[0]
2. 获取导师信息：张三教授
3. 回复："张三教授是机器学习方向的，学生评价很高..."
```

```
用户："这个导师的评价如何？"
Agent 处理：
1. 读取 page_context.selected_advisor
2. 如果有选中的导师，介绍该导师
3. 如果没有，询问："你是指哪位导师呢？"
```

#### 能力 2：感知页面变化

```
场景：排行榜已更新
page_context.ranking_filters = {"school": "北京大学", "major": "计算机科学与技术"}

用户："有哪些导师？"
Agent 处理：
1. 检测到排行榜已筛选
2. 回复："目前显示的是北大计算机系的导师，排名第一的是张三教授..."
```

#### 能力 3：上下文连贯

```
场景：用户在导师详情页
page_context.current_page = "detail"
page_context.selected_advisor = {"name": "张三", "id": "12345"}

用户："他的学生评价怎么样？"
Agent 处理：
1. 识别"他"指的是张三
2. 调用 get_advisor_reviews("12345")
3. 回复："张三教授的学生评价整体很好，平均 4.5 分..."
```

### 3.3 页面状态更新

Agent 的工具调用会触发页面状态更新：

```
update_ranking()
  → 页面更新排行榜
  → page_context.ranking_filters 更新
  → page_context.visible_advisors 更新

get_advisor_detail()
  → 页面跳转到详情页
  → page_context.current_page = "detail"
  → page_context.selected_advisor 更新
```

---

## 4. 对话流程示例

### 4.1 完整流程

```
[用户进入首页，page_context.current_page = "home"]

用户: "我想考北京大学计算机系"

Agent 处理：
1. 提取信息：school="北京大学", major="计算机科学与技术"
2. 更新表单：update_form(school, major)
3. 检查完整性：is_complete = true
4. 触发更新：update_ranking(school, major)

Agent 输出：
{
  "voice_response": "好的，北京大学计算机系。正在为你筛选导师...",
  "tool_calls": [
    {"tool": "update_form", "params": {...}},
    {"tool": "update_ranking", "params": {...}}
  ]
}

[页面更新，显示北大计算机系导师排行榜]
[page_context.ranking_filters = {"school": "北京大学", "major": "计算机科学与技术"}]
[page_context.visible_advisors = [...]]

---

用户: "我想做机器学习，希望导师温和一点"

Agent 处理：
1. 提取偏好：research_direction="机器学习", personality="温和"
2. 更新表单：update_form(preferences)
3. 触发推荐：recommend_advisors(form)

Agent 输出：
{
  "voice_response": "根据你的需求，我推荐张三教授，他主要研究机器学习，学生评价他很温和。",
  "tool_calls": [
    {"tool": "update_form", "params": {...}},
    {"tool": "recommend_advisors", "params": {...}}
  ]
}

[页面高亮推荐的导师]

---

用户: "第一个导师怎么样？"

Agent 处理：
1. 读取 page_context.visible_advisors[0]
2. 获取导师信息：张三教授
3. 介绍导师

Agent 输出：
{
  "voice_response": "张三教授是机器学习方向的，发表了 50 多篇论文，学生评价 4.5 分，很受欢迎。",
  "tool_calls": []
}

---

用户: "我想看看他的详细信息"

Agent 处理：
1. 识别"他"指的是张三（从上下文）
2. 调用详情接口

Agent 输出：
{
  "voice_response": "好的，这是张三教授的详细信息。",
  "tool_calls": [
    {"tool": "get_advisor_detail", "params": {"advisor_id": "12345"}}
  ]
}

[页面跳转到导师详情页]
[page_context.current_page = "detail"]
[page_context.selected_advisor = {"name": "张三", "id": "12345"}]
```

---

## 5. 会话管理

### 5.1 单次会话

- 会话开始：用户进入页面
- 会话结束：用户关闭页面或刷新
- 数据清空：表单、对话历史全部清空

### 5.2 会话状态

```json
{
  "session": {
    "session_id": "uuid-xxxx",
    "start_time": "2026-01-12 10:30:00",
    "user_form": {...},
    "conversation_history": [
      {"role": "user", "content": "我想考北大计算机系"},
      {"role": "assistant", "content": "好的，北京大学计算机系..."}
    ],
    "page_context": {...}
  }
}
```

### 5.3 会话持久化（未来扩展）

暂不实现，但预留接口：
- 用户登录后可保存会话
- 下次进入自动恢复

---

## 6. 错误处理

### 6.1 信息提取失败

```
用户: "我想考研"

Agent 处理：
1. 提取信息：无法提取学校和专业
2. 主动询问

Agent 输出：
{
  "voice_response": "好的，请问你想考哪个学校的哪个专业呢？",
  "tool_calls": []
}
```

### 6.2 API 调用失败

```
update_ranking() 失败

Agent 输出：
{
  "voice_response": "抱歉，数据加载失败了，请稍后再试。",
  "tool_calls": []
}
```

### 6.3 页面状态不一致

```
用户: "第一个导师怎么样？"
page_context.visible_advisors = []  // 空列表

Agent 输出：
{
  "voice_response": "目前还没有导师列表，请先告诉我你的学校和专业。",
  "tool_calls": []
}
```

---

## 7. 技术实现要点

### 7.1 LLM Prompt 设计

在系统 Prompt 中添加：

```
你是一个导师推荐助手。你需要：

1. 从用户对话中提取信息并填写表单
2. 表单字段：
   - school（必填）
   - major（必填）
   - research_direction（可选）
   - preferences.personality（可选）

3. 当 school 和 major 都填写后，自动调用 update_ranking 工具

4. 你能看到页面上的内容（page_context），当用户说"第一个"、"这个"时，
   你需要从 page_context 中找到对应的导师

5. 你的回复必须简洁（2-3句话），适合语音播放

6. 每次回复包含：
   - voice_response：语音回复内容
   - tool_calls：需要调用的工具列表
```

### 7.2 工具调用实现

使用 Function Calling 机制：

```python
tools = [
    {
        "name": "update_form",
        "description": "更新用户表单信息",
        "parameters": {
            "type": "object",
            "properties": {
                "school": {"type": "string"},
                "major": {"type": "string"},
                "research_direction": {"type": "string"},
                "preferences": {"type": "object"}
            }
        }
    },
    {
        "name": "update_ranking",
        "description": "更新导师排行榜（需要 school 和 major）",
        "parameters": {
            "type": "object",
            "properties": {
                "school": {"type": "string"},
                "major": {"type": "string"}
            },
            "required": ["school", "major"]
        }
    },
    # ... 其他工具
]
```

### 7.3 页面状态同步

前端 → Agent：
```javascript
// 前端发送页面状态
const pageContext = {
  current_page: "ranking",
  visible_advisors: getVisibleAdvisors(),
  selected_advisor: getSelectedAdvisor(),
  ranking_filters: getCurrentFilters()
};

sendToAgent(userInput, pageContext);
```

Agent → 前端：
```javascript
// 前端接收 Agent 响应
const response = await getAgentResponse();

// 播放语音
playVoice(response.voice_response);

// 执行工具调用
response.tool_calls.forEach(call => {
  if (call.tool === "update_ranking") {
    updateRankingUI(call.params);
  }
  // ... 其他工具
});
```

---

## 8. 待讨论问题

1. 表单字段是否需要增加？（如：学位类型、入学年份等）
2. 推荐算法的权重如何设置？
3. 是否需要支持多导师对比？
4. 页面感知的粒度是否足够？
5. 错误处理是否完善？

---

## 9. 下一步计划

1. 确定表单字段的最终版本
2. 设计推荐算法的详细逻辑
3. 完善页面感知的具体实现
4. 设计前后端接口协议
5. 编写测试用例
