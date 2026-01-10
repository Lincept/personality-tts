"""
配置加载工具 - 支持从 .env 文件或 config/api_keys.json 加载配置
"""
import os
import json
from typing import Dict, Any


class ConfigLoader:
    def __init__(self):
        self.config = {}
        self._load_config()

    def _load_config(self):
        """加载配置,优先使用 .env 文件"""
        # 尝试从 .env 文件加载
        env_file = ".env"
        if os.path.exists(env_file):
            self._load_from_env(env_file)

        # 如果 .env 中没有配置,则从 JSON 文件加载
        if not self.config:
            json_file = "config/api_keys.json"
            if os.path.exists(json_file):
                self._load_from_json(json_file)

    def _load_from_env(self, env_file: str):
        """从 .env 文件加载配置"""
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue

                # 解析键值对
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # 跳过占位符
                    if value and not value.startswith('your_'):
                        os.environ[key] = value

        # 构建配置字典
        self.config = {
            "qwen3_tts": {
                "api_key": os.getenv("QWEN3_API_KEY", ""),
                "base_url": "https://dashscope.aliyuncs.com/api/v1"
            },
            "volcengine_seed2": {
                "app_id": os.getenv("VOLCENGINE_APP_ID", ""),
                "access_token": os.getenv("VOLCENGINE_ACCESS_TOKEN", ""),
                "base_url": "https://openspeech.bytedance.com/api/v1"
            },
            "minimax": {
                "api_key": os.getenv("MINIMAX_API_KEY", ""),
                "group_id": os.getenv("MINIMAX_GROUP_ID", ""),
                "base_url": "https://api.minimax.chat/v1"
            },
            "openai_compatible": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4")
            }
        }

    def _load_from_json(self, json_file: str):
        """从 JSON 文件加载配置"""
        with open(json_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config

    def validate_config(self) -> Dict[str, bool]:
        """验证配置是否完整"""
        validation = {}

        # 检查 Qwen3
        qwen3 = self.config.get("qwen3_tts", {})
        validation["qwen3"] = bool(qwen3.get("api_key") and
                                   not qwen3.get("api_key").startswith("YOUR_"))

        # 检查火山引擎
        volcengine = self.config.get("volcengine_seed2", {})
        validation["volcengine"] = bool(volcengine.get("app_id") and
                                       volcengine.get("access_token") and
                                       not volcengine.get("app_id").startswith("YOUR_"))

        # 检查 MiniMax
        minimax = self.config.get("minimax", {})
        validation["minimax"] = bool(minimax.get("api_key") and
                                    minimax.get("group_id") and
                                    not minimax.get("api_key").startswith("YOUR_"))

        # 检查 OpenAI
        openai = self.config.get("openai_compatible", {})
        validation["openai"] = bool(openai.get("api_key") and
                                   not openai.get("api_key").startswith("YOUR_"))

        return validation

    def print_status(self):
        """打印配置状态"""
        validation = self.validate_config()

        print("\n配置状态:")
        print("=" * 50)
        print(f"✓ Qwen3 TTS:      {'已配置' if validation['qwen3'] else '未配置'}")
        print(f"✓ 火山引擎 Seed2: {'已配置' if validation['volcengine'] else '未配置'}")
        print(f"✓ MiniMax TTS:    {'已配置' if validation['minimax'] else '未配置'}")
        print(f"✓ OpenAI LLM:     {'已配置' if validation['openai'] else '未配置'}")
        print("=" * 50)

        if not any(validation.values()):
            print("\n⚠️  警告: 没有配置任何 API 密钥!")
            print("请编辑 .env 文件或 config/api_keys.json 填入你的 API 密钥")

        return validation
