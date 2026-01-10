# 快速配置指南

## 方式一: 使用 .env 文件 (推荐)

1. 打开项目根目录下的 `.env` 文件
2. 将占位符替换为你的真实 API 密钥

```bash
# 编辑 .env 文件
nano .env
# 或
vim .env
# 或使用任何文本编辑器
```

**示例:**
```bash
# Qwen3 TTS
QWEN3_API_KEY=sk-abc123def456...

# 火山引擎 Seed2
VOLCENGINE_APP_ID=1234567890
VOLCENGINE_ACCESS_TOKEN=abc123def456...

# MiniMax
MINIMAX_API_KEY=eyJhbGc...
MINIMAX_GROUP_ID=1234567890

# OpenAI 兼容 LLM
OPENAI_API_KEY=sk-abc123...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

## 方式二: 使用 JSON 配置文件

编辑 `config/api_keys.json` 文件:

```json
{
  "qwen3_tts": {
    "api_key": "你的_qwen3_api_key",
    "base_url": "https://dashscope.aliyuncs.com/api/v1"
  },
  "volcengine_seed2": {
    "app_id": "你的_volcengine_app_id",
    "access_token": "你的_volcengine_access_token",
    "base_url": "https://openspeech.bytedance.com/api/v1"
  },
  "minimax": {
    "api_key": "你的_minimax_api_key",
    "group_id": "你的_minimax_group_id",
    "base_url": "https://api.minimax.chat/v1"
  },
  "openai_compatible": {
    "api_key": "你的_openai_api_key",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  }
}
```

## 获取 API 密钥

### Qwen3 TTS (通义千问)
1. 访问: https://dashscope.console.aliyun.com/
2. 注册/登录阿里云账号
3. 开通 DashScope 服务
4. 创建 API Key

### 火山引擎 Seed2
1. 访问: https://console.volcengine.com/speech/app
2. 注册/登录火山引擎账号
3. 创建语音合成应用
4. 获取 App ID 和 Access Token

### MiniMax
1. 访问: https://api.minimax.chat/
2. 注册/登录 MiniMax 账号
3. 创建应用
4. 获取 API Key 和 Group ID

### OpenAI (或兼容服务)
1. OpenAI 官方: https://platform.openai.com/api-keys
2. 或使用其他兼容 OpenAI 格式的服务:
   - 通义千问: https://dashscope.console.aliyun.com/
   - 智谱 GLM: https://open.bigmodel.cn/
   - DeepSeek: https://platform.deepseek.com/

## 验证配置

运行以下命令检查配置是否正确:

```bash
python -c "from src.config_loader import ConfigLoader; ConfigLoader().print_status()"
```

## 注意事项

1. **不要泄露 API 密钥**: `.env` 和 `config/api_keys.json` 已添加到 `.gitignore`
2. **最少配置**: 至少需要配置一个 TTS 服务和一个 LLM 服务才能运行
3. **优先级**: 如果同时存在 `.env` 和 `config/api_keys.json`,优先使用 `.env`

## 开始使用

配置完成后,运行:

```bash
python src/main.py
```
