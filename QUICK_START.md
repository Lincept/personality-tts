# 🎉 测试成功！

你的 LLM + TTS 项目已经可以正常运行了！

## ✅ 已验证功能

- **LLM 流式对话**: Qwen-Plus 模型正常工作
- **TTS 语音合成**: Qwen3 TTS (Cherry 语音) 正常工作
- **音频播放**: macOS afplay 自动播放

## 🚀 快速使用

### 1. 交互式模式（推荐）

```bash
python src/main.py
```

然后你可以：
- 直接输入问题，AI 会回答并朗读
- 输入 `/voices` 查看可用语音
- 输入 `/quit` 退出

### 2. 快速测试

```bash
python src/main.py test
```

### 3. 运行示例

```bash
python examples/simple_example.py
```

## 🎤 可用的语音

Qwen3 TTS 支持多种语音，当前使用的是 **Cherry (芊悦)**。

其他可选语音：
- **Serena** - 温柔小姐姐
- **Ethan** - 阳光男声
- **Chelsie** - 二次元女友
- **Stella** - 知性优雅
- **Lyra** - 清新甜美
- **Aria** - 专业播音
- 等等...

在交互模式中输入 `/voices` 查看完整列表。

## 📁 生成的音频文件

所有生成的音频保存在：
```
data/audios/
```

## 🔧 配置其他 TTS 服务

如果你想测试火山引擎或 MiniMax TTS，编辑 `.env` 文件添加对应的 API 密钥：

```bash
# 火山引擎 Seed2
VOLCENGINE_APP_ID=你的_app_id
VOLCENGINE_ACCESS_TOKEN=你的_access_token

# MiniMax
MINIMAX_API_KEY=你的_api_key
MINIMAX_GROUP_ID=你的_group_id
```

然后在交互模式中使用：
```
/provider volcengine
/provider minimax
```

## 💡 提示

- 生成的音频文件会保存在 `data/audios/` 目录
- Qwen3 TTS 返回的是 WAV 格式
- 音频 URL 有效期为 24 小时
- 按字符计费，一个汉字 = 2 个字符

## 🎯 下一步

试试这些命令：
```bash
# 进入交互模式
python src/main.py

# 然后输入：
你好，请给我讲个笑话
今天天气怎么样？
请用一句话介绍人工智能
```

享受你的 AI 语音助手吧！🎊
