"""
配置加载工具 - 支持从 .env 文件或 config/api_keys.json 加载配置
"""
import os
import json
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    def __init__(self):
        self.config = {}
        self._load_config()

    @staticmethod
    def _get_env(*keys: str, default: str = None) -> str:
        """Return first non-empty env var among keys."""
        for k in keys:
            v = os.getenv(k)
            if v is not None and str(v).strip() != "":
                return v
        return default

    def _load_config(self):
        """加载配置,优先使用 .env 文件"""
        # 加载 .env 文件到环境变量
        load_dotenv()

        # 尝试从 JSON 文件加载基础配置
        json_file = "config/api_keys.json"
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}

        # 如果 JSON 缺失或不完整，从环境变量补齐常用配置
        # 1) DashScope（Qwen3 TTS / ASR 常用）
        dashscope_key = self._get_env("QWEN3_API_KEY", "DASHSCOPE_API_KEY")
        if dashscope_key:
            self.config.setdefault("qwen3_tts", {})
            self.config["qwen3_tts"].setdefault("api_key", dashscope_key)

        # 2) OpenAI 兼容 LLM
        openai_key = self._get_env("OPENAI_API_KEY")
        openai_base_url = self._get_env("OPENAI_BASE_URL")
        openai_model = self._get_env("OPENAI_MODEL")
        if openai_key or openai_base_url or openai_model:
            self.config.setdefault("openai_compatible", {})
            if openai_key:
                self.config["openai_compatible"].setdefault("api_key", openai_key)
            if openai_base_url:
                self.config["openai_compatible"].setdefault("base_url", openai_base_url)
            if openai_model:
                self.config["openai_compatible"].setdefault("model", openai_model)

        # 3) 火山引擎 Seed2
        volc_app_id = self._get_env("VOLCENGINE_APP_ID")
        volc_api_key = self._get_env("VOLCENGINE_API_KEY")
        volc_access_token = self._get_env("VOLCENGINE_ACCESS_TOKEN")
        if volc_app_id or volc_api_key or volc_access_token:
            self.config.setdefault("volcengine_seed2", {})
            if volc_app_id:
                self.config["volcengine_seed2"].setdefault("app_id", volc_app_id)
            if volc_access_token:
                self.config["volcengine_seed2"].setdefault("access_token", volc_access_token)
            if volc_api_key:
                self.config["volcengine_seed2"].setdefault("api_key", volc_api_key)

        # 4) MiniMax
        minimax_api_key = self._get_env("MINIMAX_API_KEY")
        minimax_group_id = self._get_env("MINIMAX_GROUP_ID")
        if minimax_api_key or minimax_group_id:
            self.config.setdefault("minimax", {})
            if minimax_api_key:
                self.config["minimax"].setdefault("api_key", minimax_api_key)
            if minimax_group_id:
                self.config["minimax"].setdefault("group_id", minimax_group_id)

        # 5) Mem0（即使 JSON 不存在也给出默认结构）
        self.config.setdefault("mem0", {})
        # JSON -> env 覆盖仍在下方处理

        # 从环境变量覆盖 mem0 配置
        # 从 .env 读取配置，覆盖 JSON 中的值
        self.config["mem0"]["enable_mem0"] = os.getenv(
            "ENABLE_MEM0",
            str(self.config["mem0"].get("enable_mem0", "true"))
        ).lower() == "true"
        self.config["mem0"]["enable_graph"] = os.getenv(
            "ENABLE_GRAPH",
            str(self.config["mem0"].get("enable_graph", "false"))
        ).lower() == "true"
        # 兼容不同变量名：MEM0_USER_ID / DEFAULT_USER_ID
        self.config["mem0"]["user_id"] = self._get_env(
            "MEM0_USER_ID",
            "DEFAULT_USER_ID",
            default=self.config["mem0"].get("user_id", "default_user")
        )

        # Neo4j 配置
        if os.getenv("NEO4J_URL"):
            self.config["mem0"]["neo4j_url"] = os.getenv("NEO4J_URL")
        if os.getenv("NEO4J_USERNAME"):
            self.config["mem0"]["neo4j_username"] = os.getenv("NEO4J_USERNAME")
        if os.getenv("NEO4J_PASSWORD"):
            self.config["mem0"]["neo4j_password"] = os.getenv("NEO4J_PASSWORD")

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
        validation["volcengine"] = bool(
            volcengine.get("app_id") and
            (volcengine.get("api_key") or volcengine.get("access_token")) and
            not volcengine.get("app_id").startswith("YOUR_")
        )

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

        print("\n✓ 配置加载完成")

        # 显示 Mem0 状态
        mem0_config = self.config.get("mem0", {})
        mem0_enabled = mem0_config.get("enable_mem0", False)
        graph_enabled = mem0_config.get("enable_graph", False)

        if mem0_enabled:
            print(f"✓ Mem0 记忆已启用")
            if graph_enabled:
                print(f"✓ 知识图谱已启用")
            else:
                print(f"  知识图谱未启用（仅向量存储）")

        return validation
