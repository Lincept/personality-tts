# LLM + TTS API 测试项目

这个项目用于测试大语言模型(LLM)与文本转语音(TTS)服务的集成效果。

## 功能特性

- ✅ 支持 OpenAI 兼容的 LLM API (流式输出)
- ✅ 支持三种 TTS 服务:
  - Qwen3 TTS (通义千问3)
  - 火山引擎 Seed2
  - MiniMax TTS
- ✅ 实时音频播放
- ✅ 交互式对话模式
- ✅ TTS 提供商对比测试

## 项目结构

```
llm-tts-api-test/
├── config/
│   ├── api_keys.json          # API 密钥配置
│   └── test_config.json       # 测试配置
├── src/
│   ├── llm/
│   │   └── llm_client.py      # LLM 客户端
│   ├── tts/
│   │   ├── qwen3_tts.py       # Qwen3 TTS
│   │   ├── volcengine_tts.py  # 火山引擎 TTS
│   │   └── minimax_tts.py     # MiniMax TTS
│   ├── audio/
│   │   └── player.py          # 音频播放器
│   └── main.py                # 主测试脚本
├── data/
│   └── audios/                # 生成的音频文件
├── requirements.txt           # Python 依赖
└── README.md                  # 项目说明
```

## 安装

1. 克隆或下载项目

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 配置 API 密钥:

编辑 `config/api_keys.json` 文件,填入你的 API 密钥:

```json
{
  "qwen3_tts": {
    "api_key": "YOUR_QWEN3_API_KEY"
  },
  "volcengine_seed2": {
    "app_id": "YOUR_VOLCENGINE_APP_ID",
    "access_token": "YOUR_VOLCENGINE_ACCESS_TOKEN"
  },
  "minimax": {
    "api_key": "YOUR_MINIMAX_API_KEY",
    "group_id": "YOUR_MINIMAX_GROUP_ID"
  },
  "openai_compatible": {
    "api_key": "YOUR_OPENAI_API_KEY",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  }
}
```

## 使用方法

### 1. 交互式模式 (推荐)

```bash
python src/main.py interactive
```

或直接运行:

```bash
python src/main.py
```

**交互式命令:**
- 直接输入文字进行对话
- `/quit` - 退出程序
- `/provider <name>` - 切换 TTS 提供商 (qwen3/volcengine/minimax)
- `/compare` - 对比所有 TTS 提供商的效果
- `/voices` - 查看当前 TTS 的可用语音

### 2. 快速测试

```bash
python src/main.py test
```

### 3. 对比测试

```bash
python src/main.py compare
```

## 示例

### 基本对话

```python
from src.main import LLMTTSTest

test = LLMTTSTest()
test.chat_and_speak(
    prompt="你好,请介绍一下你自己",
    tts_provider="qwen3",
    play_audio=True,
    stream=True
)
```

### 对比不同 TTS 提供商

```python
test = LLMTTSTest()
test.compare_tts_providers(
    prompt="今天天气真不错,适合出去散步",
    play_audio=True
)
```

## API 说明

### LLM 客户端

```python
from src.llm.llm_client import LLMClient

client = LLMClient(
    api_key="your_api_key",
    base_url="https://api.openai.com/v1",
    model="gpt-4"
)

# 流式对话
for chunk in client.chat_stream(messages=[...]):
    print(chunk, end="")
```

### TTS 客户端

```python
from src.tts.qwen3_tts import Qwen3TTS

tts = Qwen3TTS(api_key="your_api_key")
result = tts.synthesize(
    text="你好世界",
    output_path="output.mp3"
)
```

### 音频播放

```python
from src.audio.player import AudioPlayer

player = AudioPlayer()
player.play("audio.mp3", blocking=True)
```

## 配置说明

### test_config.json

```json
{
  "tts_providers": ["qwen3", "volcengine", "minimax"],
  "default_voice": {
    "qwen3": "zhifeng_emo",
    "volcengine": "zh_female_qingxin",
    "minimax": "female-tianmei"
  },
  "audio_format": "mp3",
  "sample_rate": 24000,
  "output_dir": "data/audios",
  "llm_config": {
    "temperature": 0.7,
    "max_tokens": 2000,
    "stream": true
  }
}
```

## 支持的语音

### Qwen3 TTS
- zhifeng_emo (知锋情感语音)
- zhiyan_emo (知燕情感语音)
- zhimi_emo (知米情感语音)
- zhixiao (知晓)
- zhichu (知楚)
- zhimiao (知妙)

### 火山引擎 Seed2
- zh_female_qingxin (清新女声)
- zh_male_chunhou (醇厚男声)
- zh_female_wanxin (婉心女声)
- zh_male_qingrun (清润男声)
- zh_female_tianmei (甜美女声)
- zh_male_ziran (自然男声)
- BV700_V2_streaming (Seed2 流式语音)

### MiniMax
- female-tianmei (甜美女声)
- female-wenrou (温柔女声)
- male-qingse (青涩男声)
- male-chenwen (沉稳男声)
- presenter_male (男性主播)
- presenter_female (女性主播)
- audiobook_male_1 (男性有声书1)
- audiobook_female_1 (女性有声书1)

## 系统要求

- Python 3.8+
- macOS / Linux / Windows
- 音频播放器 (macOS 自带 afplay, Linux 需要 ffplay/mpg123, Windows 自带)

## 注意事项

1. **API 密钥安全**: 不要将 `config/api_keys.json` 提交到公开仓库
2. **API 限流**: 注意各平台的速率限制
3. **成本控制**: 监控 API 调用成本
4. **网络连接**: 确保网络连接稳定

## 故障排除

### 音频无法播放

**macOS**: 自动使用 afplay,无需额外配置

**Linux**: 安装音频播放器
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# 或
sudo apt-get install mpg123
```

**Windows**: 安装 ffmpeg 并添加到 PATH

### API 调用失败

1. 检查 API 密钥是否正确
2. 检查网络连接
3. 查看 API 配额是否用完
4. 检查 base_url 是否正确

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request!
