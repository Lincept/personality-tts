"""
Mem0 记忆管理器 - 为语音助手提供长期记忆能力
"""
from typing import List, Dict, Optional
import os


class Mem0Manager:
    """Mem0 记忆管理器"""

    def __init__(self, config: Dict):
        """
        初始化 Mem0

        Args:
            config: 配置字典，包含：
                - llm_api_key: OpenAI API Key（用于记忆提取）
                - llm_base_url: OpenAI Base URL
                - llm_model: 模型名称
                - enable_mem0: 是否启用 Mem0
        """
        self.enabled = config.get("enable_mem0", False)

        if not self.enabled:
            print("Mem0 未启用")
            return

        try:
            from mem0 import Memory

            # 构建 Mem0 配置
            # 完全使用通义千问 API（LLM + Embedding）
            mem0_config = {
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": config.get("llm_model", "qwen-turbo"),
                        "api_key": config.get("llm_api_key"),
                        "openai_base_url": config.get("llm_base_url")
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-v3",  # 通义千问 embedding 模型
                        "api_key": config.get("llm_api_key"),
                        "openai_base_url": config.get("llm_base_url"),
                        "embedding_dims": 1024  # 通义千问支持的维度
                    }
                },
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": "personality_tts_memory",
                        "path": "./data/qdrant",
                        "embedding_model_dims": 1024  # 确保向量数据库使用正确的维度
                    }
                }
            }

            self.memory = Memory.from_config(mem0_config)
            # print("✓ Mem0 初始化成功")  # 静默初始化

        except ImportError:
            print("⚠️  警告: mem0ai 未安装，请运行: pip install mem0ai")
            self.enabled = False
        except Exception as e:
            print(f"⚠️  Mem0 初始化失败: {e}")
            self.enabled = False

    def search_memories(self, query: str, user_id: str, limit: int = 5) -> str:
        """
        检索相关记忆

        Args:
            query: 查询文本（当前用户输入）
            user_id: 用户ID
            limit: 返回记忆数量

        Returns:
            格式化的记忆上下文字符串
        """
        if not self.enabled:
            return ""

        try:
            results = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )

            if not results.get("results"):
                return ""

            memories = [m["memory"] for m in results["results"]]
            return "\n".join(f"- {m}" for m in memories)

        except Exception as e:
            print(f"⚠️  记忆检索失败: {e}")
            return ""

    def add_conversation(self, user_input: str, assistant_response: str, user_id: str):
        """
        保存对话到记忆

        Args:
            user_input: 用户输入
            assistant_response: 助手回复
            user_id: 用户ID
        """
        if not self.enabled:
            return

        try:
            messages = [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_response}
            ]

            self.memory.add(messages, user_id=user_id)

        except Exception as e:
            print(f"⚠️  记忆保存失败: {e}")

    def get_all_memories(self, user_id: str) -> List[Dict]:
        """
        获取用户所有记忆

        Args:
            user_id: 用户ID

        Returns:
            记忆列表
        """
        if not self.enabled:
            return []

        try:
            result = self.memory.get_all(user_id=user_id)
            return result.get("results", [])
        except Exception as e:
            print(f"⚠️  获取记忆失败: {e}")
            return []

    def clear_memories(self, user_id: str):
        """
        清除用户所有记忆

        Args:
            user_id: 用户ID
        """
        if not self.enabled:
            return

        try:
            memories = self.get_all_memories(user_id)
            for mem in memories:
                self.memory.delete(memory_id=mem["id"])
            print(f"✓ 已清除用户 {user_id} 的所有记忆")
        except Exception as e:
            print(f"⚠️  清除记忆失败: {e}")
