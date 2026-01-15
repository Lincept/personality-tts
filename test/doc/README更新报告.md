# README 更新报告

## 更新时间

2026-01-15

## 更新内容

### 1. 新增"命令行参数说明"部分

#### Python 模块运行参数 `-m`

**作用**：将 Python 文件作为模块来运行

**推荐使用 `-m` 的原因**：
- ✅ 模块导入更可靠
- ✅ 符合 Python 最佳实践
- ✅ 更好地处理模块导入路径

**对比**：
```bash
# 方式 1：直接运行（不推荐）
python3 src/main.py --role natural

# 方式 2：使用 -m 参数（推荐）
python3 -m src.main --role natural
```

#### 角色参数 `--role`

**作用**：指定 AI 助手的个性、说话风格和行为特征

**不加 `--role` 的效果**：
- 📋 会显示角色选择菜单
- 🎯 需要交互式选择角色
- 🔄 每次启动都需要选择

**加 `--role` 的效果**：
- ✅ 直接使用指定的角色
- ✅ 快速启动，无需选择
- ✅ 适合已确定角色的场景

### 2. 新增"可用角色列表"（表格形式）

| 角色ID | 名称 | 个性 | 风格 | 适用场景 |
|---------|------|------|------|---------|
| `natural` | 自然助手 | 自然、友好、不做作 | 像朋友一样聊天 | 日常对话、轻松交流 |
| `xuejie` | 导师评价学姐助手 | 温柔、专业、靠谱 | 专业咨询 + 学姐关怀 | 导师评价、选导师建议 |
| `funny` | 幽默助手 | 风趣、搞笑、机智 | 幽默对话 | 轻松娱乐、调节气氛 |
| `friendly` | 友好助手 | 友好、热情 | 热情交流 | 友好互动、热情服务 |
| `professional` | 专业助手 | 专业、严谨 | 正式对话 | 专业咨询、正式场合 |
| `companion` | 陪伴助手 | 温暖、关怀 | 温暖陪伴 | 情感陪伴、温暖交流 |

### 3. 新增"角色详细说明"

每个角色的详细说明：

- **natural（自然助手）**
  - 特点：自然、友好、不做作
  - 风格：像朋友一样聊天
  - 回答：简短（2-3句话，最多50字）
  - 特殊功能：主动保存用户记忆

- **xuejie（导师评价学姐助手）**
  - 特点：温柔、专业、靠谱
  - 风格：专业咨询 + 学姐关怀
  - 专长：导师评价、选导师建议
  - 限制：只处理导师评价相关的事

- **funny（幽默助手）**
  - 特点：风趣、搞笑、机智
  - 风格：幽默对话
  - 适用：轻松娱乐、调节气氛

- **friendly（友好助手）**
  - 特点：友好、热情
  - 风格：热情交流
  - 适用：友好互动、热情服务

- **professional（专业助手）**
  - 特点：专业、严谨
  - 风格：正式对话
  - 适用：专业咨询、正式场合

- **companion（陪伴助手）**
  - 特点：温暖、关怀
  - 风格：温暖陪伴
  - 适用：情感陪伴、温暖交流

### 4. 更新"运行"部分

#### 文字对话模式

新增了不同角色的使用示例：

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
python3 -m src.main --text
```

#### 语音对话模式

新增了详细的参数组合示例：

```bash
# 推荐方式：禁用 AEC + 使用耳机（最稳定）
python3 -m src.main --voice --no-aec

# 指定角色 - 学姐助手 + 耳机模式
python3 -m src.main --voice --no-aec --role xuejie

# 指定角色 - 自然助手 + 耳机模式
python3 -m src.main --voice --no-aec --role natural

# 实验性：启用 AEC（需要聚合设备）
python3 -m src.main --voice --device-index <聚合设备索引>

# 指定 ASR 模型 - Paraformer v2（默认）
python3 -m src.main --voice --no-aec --asr-model paraformer-realtime-v2

# 指定 ASR 模型 - FunASR 2025
python3 -m src.main --voice --no-aec --asr-model fun-asr-realtime-2025-11-07

# 组合使用：AEC + 指定角色 + 指定 ASR 模型
python3 -m src.main --voice --device-index <索引> --role xuejie --asr-model paraformer-realtime-v2
```

### 5. 新增"参数组合示例"部分

提供了更多实用的参数组合示例：

```bash
# 文字模式 + 指定角色
python3 -m src.main --text --role natural

# 语音模式 + 耳机模式 + 指定角色
python3 -m src.main --voice --no-aec --role xuejie

# 语音模式 + AEC + 指定角色 + 指定 ASR 模型
python3 -m src.main --voice --device-index 2 --role natural --asr-model paraformer-realtime-v2

# 列出设备（查看可用的音频设备）
python3 -m src.main --list-devices

# 检查 ASR 鉴权（验证 API Key 是否有效）
python3 -m src.main --check-asr
```

### 6. 新增"语音对话模式退出命令"部分

说明了在语音对话模式中如何退出：

```
退出
再见
拜拜
结束对话
关闭程序
```

## 改进点

### 1. 参数解释更清晰

- ✅ 详细解释了 `-m` 参数的作用和推荐原因
- ✅ 详细解释了 `--role` 参数的作用和效果
- ✅ 提供了加与不加 `--role` 的对比

### 2. 角色说明更完整

- ✅ 使用表格形式展示所有角色
- ✅ 为每个角色提供了详细的说明
- ✅ 说明了每个角色的特点和适用场景

### 3. 使用示例更丰富

- ✅ 提供了不同角色的使用示例
- ✅ 提供了参数组合示例
- ✅ 涵盖了常见的使用场景

### 4. 退出方式更明确

- ✅ 说明了语音对话模式的退出命令
- ✅ 提供了多种退出方式

## 测试验证

### 帮助命令测试

```bash
$ python3 -m src.main --help
```
✅ 通过 - 成功显示所有参数说明

### 角色参数测试

```bash
$ python3 -m src.main --role natural --help
```
✅ 通过 - 参数解析正确

## 文件变更

### 修改的文件

- `/Users/epic-lin/Documents/code/personality-tts/README.md`
  - 新增"命令行参数说明"部分
  - 新增"可用角色列表"（表格形式）
  - 新增"角色详细说明"
  - 更新"运行"部分
  - 新增"参数组合示例"部分
  - 新增"语音对话模式退出命令"部分

## 总结

✅ README 文档已全面更新
✅ 添加了详细的参数解释
✅ 添加了完整的角色说明
✅ 添加了丰富的使用示例
✅ 添加了退出命令说明

用户现在可以：
- 清楚地理解 `-m` 参数的作用
- 清楚地理解 `--role` 参数的作用
- 了解所有可用的角色及其特点
- 快速找到适合自己需求的命令示例
- 了解如何正确退出程序
