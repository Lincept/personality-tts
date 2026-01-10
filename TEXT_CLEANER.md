# 🔧 文本清理功能

## 问题

LLM 输出包含 Markdown 格式符号，TTS 会把这些符号读出来，导致：
- "星星星 La Sportiva 星星星" （`**La Sportiva**`）
- "井号井号井号 标题" （`### 标题`）
- "横线横线横线" （`---`）
- "减号 列表项" （`- 列表项`）

## 解决方案

在发送到 TTS 前，自动清理 Markdown 格式符号：

```python
from src.text_cleaner import TextCleaner

cleaner = TextCleaner()

# 清理单个文本块
chunk = "**La Sportiva**"
cleaned = cleaner.clean_chunk(chunk)  # "La Sportiva"

# 判断是否应该发送
if cleaner.should_send_to_tts(cleaned):
    tts.send_text(cleaned)
```

## 清理规则

### 移除的符号

1. **Markdown 标题**: `###` → 空
2. **粗体/斜体**: `**文本**` → `文本`
3. **列表符号**: `- 项目` → `项目`
4. **编号列表**: `1. 项目` → `项目`
5. **分隔线**: `---` → 空（不发送）
6. **代码块**: `` `代码` `` → `代码`

### 保留的内容

- ✅ 普通文本
- ✅ 标点符号（。，！？等）
- ✅ 数字和字母
- ✅ 表情符号（可选）

## 示例

### 输入（LLM 输出）

```
### 1. **La Sportiva**（意大利）
- **特点**：专业性强
- **推荐型号**：
  - **Tarantulace**：适合初学者
---
```

### 输出（发送到 TTS）

```
1. La Sportiva（意大利）
特点：专业性强
推荐型号：
Tarantulace：适合初学者
```

## 效果对比

### 之前
```
AI: "星星星 La Sportiva 星星星 括号 意大利 括号
     横线 星星星 特点 星星星 冒号 专业性强"
```

### 现在
```
AI: "La Sportiva 意大利
     特点：专业性强"
```

**完全自然流畅！**

## 技术实现

### 实时管道集成

```python
# 在 RealtimeStreamingPipeline 中
for chunk in llm_stream:
    # 显示原始文本（包含格式）
    print(chunk, end='', flush=True)

    # 清理文本
    cleaned_chunk = cleaner.clean_chunk(chunk)

    # 只发送有内容的文本
    if cleaner.should_send_to_tts(cleaned_chunk):
        tts.send_text(cleaned_chunk)
```

### 清理函数

```python
def clean_chunk(chunk: str) -> str:
    # 移除 Markdown 符号
    chunk = chunk.replace('**', '')
    chunk = chunk.replace('###', '')
    chunk = chunk.replace('---', '')

    # 移除列表符号
    chunk = re.sub(r'^\s*[-*+]\s+', '', chunk)
    chunk = re.sub(r'^\s*\d+\.\s+', '', chunk)

    return chunk
```

## 使用方法

### 自动启用

实时模式下**自动启用**文本清理，无需配置。

### 测试

```bash
python src/main.py
```

输入包含格式的问题：
```
你: 请用列表形式介绍三个攀岩鞋品牌
```

AI 会输出 Markdown 格式，但 TTS 只会读取清理后的文本。

## 自定义清理规则

编辑 `src/text_cleaner.py`：

```python
def clean_chunk(chunk: str) -> str:
    # 添加自定义规则
    chunk = chunk.replace('您的符号', '')

    return chunk
```

## 注意事项

1. **显示 vs 播放**
   - 屏幕显示：保留原始格式（方便阅读）
   - TTS 播放：使用清理后的文本（自然流畅）

2. **表情符号**
   - 默认保留表情符号
   - 如需移除，取消注释相关代码

3. **特殊符号**
   - 如果发现其他奇怪的读音，可以添加到清理规则

## 完成！

现在 AI 的语音应该完全自然流畅，不会再读出 Markdown 符号了！🎉
