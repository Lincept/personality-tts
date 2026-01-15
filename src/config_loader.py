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

    def _load_config(self):
        """加载配置,优先使用 .env 文件"""
        # 加载 .env 文件到环境变量
        load_dotenv()

        # 尝试从 JSON 文件加载基础配置
        json_file = "config/api_keys.json"
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

        # 从环境变量覆盖 mem0 配置
        if "mem0" in self.config:
            # 从 .env 读取配置，覆盖 JSON 中的值
            self.config["mem0"]["enable_mem0"] = os.getenv("ENABLE_MEM0", str(self.config["mem0"].get("enable_mem0", "true"))).lower() == "true"
            self.config["mem0"]["enable_graph"] = os.getenv("ENABLE_GRAPH", str(self.config["mem0"].get("enable_graph", "false"))).lower() == "true"
            self.config["mem0"]["user_id"] = os.getenv("DEFAULT_USER_ID", self.config["mem0"].get("user_id", "default_user"))

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
