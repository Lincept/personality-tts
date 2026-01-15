"""src.config_loader

配置加载工具。

当前约定：仅使用 `.env`（推荐且唯一的配置来源）。
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigLoader:
    def __init__(self):
        self.config = {}
        self._load_config()

    @staticmethod
    def _get_env(*keys: str, default: Optional[str] = None) -> Optional[str]:
        """Return first non-empty env var among keys."""
        for k in keys:
            v = os.getenv(k)
            if v is not None and str(v).strip() != "":
                return v
        return default

    def _load_config(self):
        """加载配置：仅从 `.env` / 环境变量读取。"""
        # 加载 .env 文件到环境变量（不会覆盖已存在的环境变量）
        load_dotenv()

        # 仅从环境变量构建配置
        self.config = {}

        # 从环境变量补齐/覆盖常用配置（.env 优先级更高）
        # 1) DashScope（Qwen3 TTS / ASR 常用）
        dashscope_key = self._get_env("QWEN3_API_KEY", "DASHSCOPE_API_KEY")
        qwen3_base_url = self._get_env("QWEN3_BASE_URL")
        if dashscope_key:
            self.config.setdefault("qwen3_tts", {})
            self.config["qwen3_tts"]["api_key"] = dashscope_key
        if qwen3_base_url:
            self.config.setdefault("qwen3_tts", {})
            self.config["qwen3_tts"]["base_url"] = qwen3_base_url

        # 2) OpenAI 兼容 LLM
        openai_key = self._get_env("OPENAI_API_KEY")
        openai_base_url = self._get_env("OPENAI_BASE_URL")
        openai_model = self._get_env("OPENAI_MODEL")
        if openai_key or openai_base_url or openai_model:
            self.config.setdefault("openai_compatible", {})
            if openai_key:
                self.config["openai_compatible"]["api_key"] = openai_key
            if openai_base_url:
                self.config["openai_compatible"]["base_url"] = openai_base_url
            if openai_model:
                self.config["openai_compatible"]["model"] = openai_model

        # 3) 火山引擎 Seed2
        volc_app_id = self._get_env("VOLCENGINE_APP_ID")
        volc_api_key = self._get_env("VOLCENGINE_API_KEY")
        volc_access_token = self._get_env("VOLCENGINE_ACCESS_TOKEN")
        volc_base_url = self._get_env("VOLCENGINE_BASE_URL")
        if volc_app_id or volc_api_key or volc_access_token or volc_base_url:
            self.config.setdefault("volcengine_seed2", {})
            if volc_app_id:
                self.config["volcengine_seed2"]["app_id"] = volc_app_id
            if volc_access_token:
                self.config["volcengine_seed2"]["access_token"] = volc_access_token
            if volc_api_key:
                self.config["volcengine_seed2"]["api_key"] = volc_api_key
            if volc_base_url:
                self.config["volcengine_seed2"]["base_url"] = volc_base_url

        # 4) MiniMax
        minimax_api_key = self._get_env("MINIMAX_API_KEY")
        minimax_group_id = self._get_env("MINIMAX_GROUP_ID")
        minimax_base_url = self._get_env("MINIMAX_BASE_URL")
        if minimax_api_key or minimax_group_id or minimax_base_url:
            self.config.setdefault("minimax", {})
            if minimax_api_key:
                self.config["minimax"]["api_key"] = minimax_api_key
            if minimax_group_id:
                self.config["minimax"]["group_id"] = minimax_group_id
            if minimax_base_url:
                self.config["minimax"]["base_url"] = minimax_base_url

        # 5) Mem0（即使 JSON 不存在也给出默认结构）
        self.config.setdefault("mem0", {})

        # 从环境变量覆盖 mem0 配置
        # 开关：仅当 env 显式设置时启用；否则默认关闭
        enable_mem0_env = os.getenv("ENABLE_MEM0")
        if enable_mem0_env is not None:
            self.config["mem0"]["enable_mem0"] = str(enable_mem0_env).strip().lower() == "true"
        else:
            self.config["mem0"]["enable_mem0"] = False

        enable_graph_env = os.getenv("ENABLE_GRAPH")
        if enable_graph_env is not None:
            self.config["mem0"]["enable_graph"] = str(enable_graph_env).strip().lower() == "true"
        else:
            self.config["mem0"]["enable_graph"] = False

        # 兼容不同变量名：MEM0_USER_ID / DEFAULT_USER_ID
        self.config["mem0"]["user_id"] = self._get_env(
            "MEM0_USER_ID",
            "DEFAULT_USER_ID",
            default=self.config["mem0"].get("user_id", "default_user")
        )

        # Mem0 使用的 LLM 配置（用于记忆提取 + embedding）
        # 优先 MEM0_LLM_*，否则回退到 OPENAI_*（openai_compatible 段）
        openai_cfg = self.config.get("openai_compatible", {})
        mem0_llm_api_key = self._get_env("MEM0_LLM_API_KEY", default=openai_cfg.get("api_key"))
        mem0_llm_base_url = self._get_env("MEM0_LLM_BASE_URL", default=openai_cfg.get("base_url"))
        mem0_llm_model = self._get_env("MEM0_LLM_MODEL", default=openai_cfg.get("model"))
        if mem0_llm_api_key:
            self.config["mem0"]["llm_api_key"] = mem0_llm_api_key
        if mem0_llm_base_url:
            self.config["mem0"]["llm_base_url"] = mem0_llm_base_url
        if mem0_llm_model:
            self.config["mem0"]["llm_model"] = mem0_llm_model

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
