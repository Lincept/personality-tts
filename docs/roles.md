# 角色参数说明

本文件详细说明了 `--role` 参数的使用方法和所有可用角色。

## 角色参数 `--role`

### 作用

指定 AI 助手的个性、说话风格和行为特征。

### 不加 `--role` 的效果

- 📋 会显示角色选择菜单
- 🎯 需要交互式选择角色
- 🔄 每次启动都需要选择

### 加 `--role` 的效果

- ✅ 直接使用指定的角色
- ✅ 快速启动，无需选择
- ✅ 适合已确定角色的场景

## 可用角色列表

| 角色ID | 名称 | 个性 | 风格 | 适用场景 |
|---------|------|------|------|---------|
| `natural` | 自然助手 | 自然、友好、不做作 | 像朋友一样聊天 | 日常对话、轻松交流 |
| `xuejie` | 导师评价学姐助手 | 温柔、专业、靠谱 | 专业咨询 + 学姐关怀 | 导师评价、选导师建议 |
| `funny` | 幽默助手 | 风趣、搞笑、机智 | 幽默对话 | 轻松娱乐、调节气氛 |
| `friendly` | 友好助手 | 友好、热情 | 热情交流 | 友好互动、热情服务 |
| `professional` | 专业助手 | 专业、严谨 | 正式对话 | 专业咨询、正式场合 |
| `companion` | 陪伴助手 | 温暖、关怀 | 温暖陪伴 | 情感陪伴、温暖交流 |

## 角色详细说明

### natural（自然助手）

**特点**：自然、友好、不做作

**风格**：像朋友一样聊天

**回答特点**：
- 简短（2-3句话，最多50字）
- 自然口语化
- 不总是问问题

**特殊功能**：
- 主动保存用户记忆
- 强调简短回答与主动保存记忆

**适用场景**：
- 日常对话
- 轻松交流
- 朋友式聊天

**使用示例**：
```bash
python3 -m src.main --role natural
python3 -m src.main --voice --no-aec --role natural
```

### xuejie（导师评价学姐助手）

**特点**：温柔、专业、靠谱

**风格**：专业咨询 + 学姐关怀

**专长**：
- 导师评价
- 选导师建议

**限制**：
- 只处理导师评价相关的事
- 不能做超出能力范围的事（如：买机票、订餐、约见面等）

**适用场景**：
- 导师评价
- 选导师建议
- 学术咨询

**使用示例**：
```bash
python3 -m src.main --role xuejie
python3 -m src.main --voice --no-aec --role xuejie
```

### funny（幽默助手）

**特点**：风趣、搞笑、机智

**风格**：幽默对话

**适用场景**：
- 轻松娱乐
- 调节气氛
- 幽默互动

**使用示例**：
```bash
python3 -m src.main --role funny
python3 -m src.main --voice --no-aec --role funny
```

### friendly（友好助手）

**特点**：友好、热情

**风格**：热情交流

**适用场景**：
- 友好互动
- 热情服务
- 客户服务

**使用示例**：
```bash
python3 -m src.main --role friendly
python3 -m src.main --voice --no-aec --role friendly
```

### professional（专业助手）

**特点**：专业、严谨

**风格**：正式对话

**适用场景**：
- 专业咨询
- 正式场合
- 商务对话

**使用示例**：
```bash
python3 -m src.main --role professional
python3 -m src.main --voice --no-aec --role professional
```

### companion（陪伴助手）

**特点**：温暖、关怀

**风格**：温暖陪伴

**适用场景**：
- 情感陪伴
- 温暖交流
- 心理支持

**使用示例**：
```bash
python3 -m src.main --role companion
python3 -m src.main --voice --no-aec --role companion
```

## 参数组合示例

### 文字对话模式

```bash
# 默认模式（会提示选择角色）
python3 -m src.main

# 指定角色 - 自然助手
python3 -m src.main --role natural

# 指定角色 - 学姐助手
python3 -m src.main --role xuejie

# 指定角色 - 幽默助手
python3 -m src.main --role funny

# 显式指定文字模式
python3 -m src.main --text --role natural
```

### 语音对话模式

```bash
# 耳机模式（推荐）+ 指定角色
python3 -m src.main --voice --no-aec --role natural
python3 -m src.main --voice --no-aec --role xuejie

# AEC 模式 + 指定角色
python3 -m src.main --voice --device-index <索引> --role natural

# 指定 ASR 模型 + 指定角色
python3 -m src.main --voice --no-aec --asr-model paraformer-realtime-v2 --role natural
python3 -m src.main --voice --no-aec --asr-model fun-asr-realtime-2025-11-07 --role funny

# 组合使用：AEC + 指定角色 + 指定 ASR 模型
python3 -m src.main --voice --device-index <索引> --role xuejie --asr-model paraformer-realtime-v2
```

## 快速开始指南

### 首次使用

如果你是第一次使用，建议：

1. **不指定角色**，查看所有角色
   ```bash
   python3 -m src.main
   ```
   程序会显示角色选择菜单，让你了解所有选项

2. **尝试不同角色**，找到最适合你的
   ```bash
   # 尝试自然助手
   python3 -m src.main --role natural
   
   # 尝试学姐助手
   python3 -m src.main --role xuejie
   
   # 尝试幽默助手
   python3 -m src.main --role funny
   ```

3. **确定角色后**，使用 `--role` 参数快速启动
   ```bash
   # 例如：确定使用自然助手
   python3 -m src.main --role natural
   ```

### 日常使用

如果你已经确定常用的角色：

```bash
# 文字对话模式 - 直接使用角色
python3 -m src.main --role natural

# 语音对话模式 - 直接使用角色
python3 -m src.main --voice --no-aec --role xuejie
```

### 场景推荐

根据你的使用场景选择角色：

| 场景 | 推荐角色 | 命令 |
|------|---------|------|
| 日常聊天、朋友对话 | natural | `python3 -m src.main --role natural` |
| 导师评价、选导师 | xuejie | `python3 -m src.main --role xuejie` |
| 轻松娱乐、调节气氛 | funny | `python3 -m src.main --role funny` |
| 客户服务、热情互动 | friendly | `python3 -m src.main --role friendly` |
| 专业咨询、正式场合 | professional | `python3 -m src.main --role professional` |
| 情感陪伴、温暖交流 | companion | `python3 -m src.main --role companion` |

## 常见问题

### Q: 如何切换角色？

**A**: 在文字对话模式中，可以使用 `/role` 命令切换角色：
```
/role natural
/role xuejie
```

### Q: 如何查看当前角色？

**A**: 使用 `/info` 命令查看当前配置，包括当前角色：
```
/info
```

### Q: 可以创建自定义角色吗？

**A**: 可以！在 `roles/` 目录下创建新的角色配置文件，参考现有角色的格式。

### Q: 角色的个性会持久化吗？

**A**: 角色选择只在当前会话中有效。如果需要持久化，可以在 `.env` 文件中设置默认角色。

## 相关链接

- [README.md](../README.md) - 项目主文档
- [命令行参数说明](../README.md#4-命令行参数说明) - 查看所有命令行参数
- [快速开始](../README.md#5-运行) - 查看快速开始指南
