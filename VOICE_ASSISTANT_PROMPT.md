# 语音助手 Prompt 系统使用指南

## 概述

语音助手 Prompt 系统专门为语音对话场景设计，确保 LLM 的输出适合通过 TTS 转换为语音。

## 核心特性

### 1. 输出格式控制

系统会强制要求 LLM：
- ✅ 简洁回答（2-3 句话，最多 50 字）
- ✅ 口语化表达
- ❌ 禁止 Markdown 格式
- ❌ 禁止特殊符号
- ❌ 禁止列表格式
- ❌ 禁止长篇大论

### 2. 多角色支持

系统提供 4 种预设角色：

| 角色 | 名称 | 特点 | 适用场景 |
|------|------|------|----------|
| `default` | 默认助手 | 友好、专业、简洁 | 通用场景 |
| `casual` | 轻松助手 | 活泼、幽默、随和 | 休闲聊天 |
| `professional` | 专业助手 | 严谨、专业、高效 | 工作咨询 |
| `companion` | 陪伴助手 | 温暖、关心、耐心 | 情感陪伴 |

### 3. 上下文管理

- **用户信息**：姓名、偏好、上下文
- **知识库**：可添加自定义知识
- **对话历史**：自动管理最近 10 轮对话

## 使用方法

### 基础使用

```python
from src.voice_assistant_prompt import VoiceAssistantPrompt

# 创建 Prompt 管理器
prompt_manager = VoiceAssistantPrompt()

# 获取消息列表
messages = prompt_manager.get_messages("你好")

# 传递给 LLM
response = llm_client.chat(messages)
```

### 设置用户信息

```python
# 设置用户名
prompt_manager.set_user_info(name="小明")

# 设置偏好
prompt_manager.set_user_info(
    preferences={"运动": "攀岩", "饮食": "素食"}
)

# 设置上下文
prompt_manager.set_user_info(
    context={"位置": "北京", "天气": "晴天"}
)
```

### 添加知识库

```python
# 添加知识
prompt_manager.add_knowledge("用户是攀岩初学者", category="运动")
prompt_manager.add_knowledge("用户周末有空", category="时间")
```

### 切换角色

```python
# 切换到轻松助手
prompt_manager.set_role("casual")

# 获取当前角色信息
role_info = prompt_manager.get_role_info()
print(role_info)  # {'name': '轻松助手', 'personality': '活泼、幽默、随和', ...}
```

### 管理对话历史

```python
# 添加对话
prompt_manager.add_conversation("user", "你好")
prompt_manager.add_conversation("assistant", "你好！有什么可以帮你的吗？")

# 查看对话摘要
summary = prompt_manager.get_conversation_summary()
print(summary)

# 清空历史
prompt_manager.clear_history()
```

## 交互模式命令

在 `main.py` 的交互模式中，可以使用以下命令：

```bash
/quit                    # 退出
/mode                    # 切换模式 (realtime/streaming/normal)
/role <角色>             # 切换角色 (default/casual/professional/companion)
/clear                   # 清空对话历史
/history                 # 查看对话历史
/setname <名字>          # 设置用户名
/addknowledge <内容>     # 添加知识库
/info                    # 查看当前配置
```

### 示例对话

```
你: /role casual
✓ 已切换到角色: 轻松助手
  风格: 轻松聊天
  特点: 活泼、幽默、随和

你: /setname 小明
✓ 用户名已设置为: 小明

你: /addknowledge 喜欢攀岩
✓ 已添加知识: 喜欢攀岩

你: 推荐一些周末活动
助手: 小明你好！既然你喜欢攀岩，周末可以去攀岩馆练练手，或者找个户外岩壁挑战一下。要不要我推荐几个地方？

你: /info
当前配置:
  模式: 实时模式 (LLM逐字→TTS→边播边放) ⚡
  角色: 轻松助手 (活泼、幽默、随和)
  TTS: qwen3
  对话轮数: 1
  知识库条目: 1
```

## 测试

### 测试 Prompt 系统

```bash
# 基础测试（不需要 API）
python test_prompt_system.py

# 真实 LLM 测试
python test_voice_assistant_real.py --test basic

# 测试不同角色
python test_voice_assistant_real.py --test roles

# 全部测试
python test_voice_assistant_real.py --test all
```

### 完整语音助手测试

```bash
# 启动交互模式
python src/main.py interactive

# 或直接运行
python src/main.py
```

## Prompt 设计原则

### 1. 明确禁止不适合语音的格式

```
绝对禁止使用：
* Markdown 格式（粗体、标题、代码块等）
* 特殊符号（*、#、-、_、```、【】、「」等）
* 列表格式（带序号或符号的列表）
* 表情符号（除非用户明确要求）
```

### 2. 提供正反示例

通过具体的错误和正确示例，让模型理解期望的输出格式：

```
错误示例：
用户：推荐攀岩鞋
助手：当然！以下是几个推荐：1. La Sportiva...

正确示例：
用户：推荐攀岩鞋
助手：我推荐 La Sportiva 的 Tarantulace，特别适合初学者。
```

### 3. 强调字数限制

```
每次回答控制在 2-3 句话以内（最多 50 字）
```

### 4. 强调语音场景

```
记住：你是在和用户语音对话，保持自然、简洁、友好！
```

## 高级配置

### 自定义角色

可以在 `VoiceAssistantConfig.ROLES` 中添加自定义角色：

```python
class VoiceAssistantConfig:
    ROLES = {
        'custom': {
            'name': '自定义助手',
            'personality': '你的特点描述',
            'style': '你的风格描述'
        }
    }
```

### 调整历史记录数量

```python
prompt_manager.max_history = 20  # 保留最近 20 轮对话
```

### 自定义输出长度

```python
# 在 VoiceAssistantConfig 中修改
MAX_OUTPUT_LENGTH = {
    'short': 30,      # 简短回答
    'medium': 60,     # 中等回答
    'long': 100       # 较长回答
}
```

## 注意事项

1. **Prompt 不是万能的**：即使有严格的 prompt，LLM 仍可能偶尔输出不符合要求的内容
2. **需要后处理**：建议配合 `text_cleaner.py` 进行文本清理
3. **温度参数**：建议使用较低的 temperature（0.7 左右）以获得更稳定的输出
4. **测试验证**：在实际使用前，务必用真实 LLM 测试 prompt 效果

## 故障排除

### 问题：LLM 仍然输出 Markdown 格式

**解决方案**：
1. 检查 prompt 是否正确应用
2. 降低 temperature 参数
3. 使用 `text_cleaner.py` 进行后处理
4. 考虑更换模型

### 问题：回答太长

**解决方案**：
1. 在 prompt 中强调字数限制
2. 在用户输入中添加"简短回答"提示
3. 使用后处理截断

### 问题：角色切换不明显

**解决方案**：
1. 清空对话历史后再切换角色
2. 在角色配置中添加更具体的描述
3. 在 prompt 中添加更多角色相关的示例

## 相关文件

- `src/voice_assistant_prompt.py` - Prompt 管理系统
- `src/text_cleaner.py` - 文本清理工具
- `src/main.py` - 主程序（包含交互模式）
- `test_prompt_system.py` - Prompt 系统测试
- `test_voice_assistant_real.py` - 真实 LLM 测试
