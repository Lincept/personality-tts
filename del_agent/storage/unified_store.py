"""
统一知识存储接口 - 支持 Mem0 和本地 JSON 存储

提供统一的接口用于后端批量处理，支持两种存储后端：
1. Mem0: 基于向量数据库的语义检索（需要 LLM API）
2. JSON: 基于本地文件的简单存储（无外部依赖）

使用方式：
    from del_agent.storage.unified_store import create_knowledge_store
    
    # 创建 JSON 存储（默认）
    store = create_knowledge_store(backend="json")
    
    # 创建 Mem0 存储
    store = create_knowledge_store(backend="mem0", config={...})
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


@dataclass
class KnowledgeRecord:
    """知识记录（统一结构）"""
    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    score: float = 0.0  # 搜索相关度分数
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
            "created_at": self.created_at
        }


class KnowledgeStore(ABC):
    """知识存储抽象接口"""
    
    @property
    @abstractmethod
    def enabled(self) -> bool:
        """是否已启用"""
        pass
    
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """后端名称"""
        pass
    
    @abstractmethod
    def insert(
        self,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        kind: str = "fact"
    ) -> bool:
        """插入记录"""
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeRecord]:
        """搜索记录"""
        pass
    
    @abstractmethod
    def get_all(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[KnowledgeRecord]:
        """获取所有记录"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass
    
    @abstractmethod
    def clear(self, user_id: Optional[str] = None) -> None:
        """清空记录"""
        pass
    
    def close(self) -> None:
        """关闭连接（可选实现）"""
        pass


class JsonKnowledgeStore(KnowledgeStore):
    """
    基于 JSON 文件的本地知识存储
    
    存储结构:
        data/knowledge_store/
            index.json          # 索引文件
            records/
                {user_id}/      # 按用户ID分组
                    {record_id}.json
    """
    
    def __init__(self, base_dir: Optional[str] = None, verbose: bool = False):
        import json
        import hashlib
        from datetime import datetime
        
        self._json = json
        self._hashlib = hashlib
        self._datetime = datetime
        
        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path(__file__).parent.parent / "data" / "knowledge_store"
        
        self._records_dir = self._base_dir / "records"
        self._index_file = self._base_dir / "index.json"
        self._verbose = verbose
        
        self._ensure_dirs()
        self._index = self._load_index()
        
        if self._verbose:
            print(f"[JSON_STORE] 初始化完成: {self._base_dir}")
            print(f"[JSON_STORE] 当前记录数: {len(self._index)}")
    
    @property
    def enabled(self) -> bool:
        return True
    
    @property
    def backend_name(self) -> str:
        return "json"
    
    def _ensure_dirs(self):
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._records_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    return self._json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_index(self):
        with open(self._index_file, "w", encoding="utf-8") as f:
            self._json.dump(self._index, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, content: str, metadata: Dict[str, Any]) -> str:
        hash_input = f"{content}:{self._json.dumps(metadata, sort_keys=True)}"
        return self._hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def insert(
        self,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        kind: str = "fact"
    ) -> bool:
        try:
            metadata = metadata or {}
            metadata["kind"] = kind
            metadata["user_id"] = user_id
            
            record_id = self._generate_id(content, metadata)
            
            if record_id in self._index:
                if self._verbose:
                    print(f"[JSON_STORE] 记录已存在: {record_id}")
                return True
            
            created_at = self._datetime.now().isoformat()
            record = {
                "id": record_id,
                "content": content,
                "metadata": metadata,
                "created_at": created_at
            }
            
            user_dir = self._records_dir / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            record_file = user_dir / f"{record_id}.json"
            with open(record_file, "w", encoding="utf-8") as f:
                self._json.dump(record, f, ensure_ascii=False, indent=2)
            
            self._index[record_id] = {
                "user_id": user_id,
                "kind": kind,
                "dimension": metadata.get("dimension", ""),
                "professor": metadata.get("professor", ""),
                "created_at": created_at,
                "file": str(record_file.relative_to(self._base_dir))
            }
            self._save_index()
            
            if self._verbose:
                print(f"[JSON_STORE] 插入成功: {record_id} ({kind})")
            
            return True
        except Exception as e:
            if self._verbose:
                print(f"[JSON_STORE] 插入失败: {e}")
            return False
    
    def _get_record(self, record_id: str) -> Optional[KnowledgeRecord]:
        if record_id not in self._index:
            return None
        try:
            file_path = self._base_dir / self._index[record_id]["file"]
            with open(file_path, "r", encoding="utf-8") as f:
                data = self._json.load(f)
            return KnowledgeRecord(
                id=data.get("id", ""),
                content=data.get("content", ""),
                metadata=data.get("metadata"),
                created_at=data.get("created_at")
            )
        except Exception:
            return None
    
    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeRecord]:
        results = []
        query_lower = query.lower()
        
        for record_id, info in self._index.items():
            if len(results) >= limit:
                break
            
            if user_id and info.get("user_id") != user_id:
                continue
            
            # 检查索引字段
            if (query_lower in info.get("professor", "").lower() or
                query_lower in info.get("dimension", "").lower()):
                record = self._get_record(record_id)
                if record:
                    results.append(record)
                continue
            
            # 检查完整内容
            record = self._get_record(record_id)
            if record and query_lower in record.content.lower():
                results.append(record)
        
        return results
    
    def get_all(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[KnowledgeRecord]:
        records = []
        count = 0
        
        for record_id, info in self._index.items():
            if count >= limit:
                break
            
            if user_id and info.get("user_id") != user_id:
                continue
            
            record = self._get_record(record_id)
            if record:
                records.append(record)
                count += 1
        
        return records
    
    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "backend": "json",
            "total_records": len(self._index),
            "storage_path": str(self._base_dir),
            "by_user": {},
            "by_dimension": {},
            "by_kind": {}
        }
        
        for info in self._index.values():
            user_id = info.get("user_id", "unknown")
            stats["by_user"][user_id] = stats["by_user"].get(user_id, 0) + 1
            
            dimension = info.get("dimension", "unknown")
            stats["by_dimension"][dimension] = stats["by_dimension"].get(dimension, 0) + 1
            
            kind = info.get("kind", "unknown")
            stats["by_kind"][kind] = stats["by_kind"].get(kind, 0) + 1
        
        return stats
    
    def clear(self, user_id: Optional[str] = None) -> None:
        import shutil
        
        if user_id:
            user_dir = self._records_dir / user_id
            if user_dir.exists():
                shutil.rmtree(user_dir)
            
            self._index = {
                k: v for k, v in self._index.items()
                if v.get("user_id") != user_id
            }
            self._save_index()
            
            if self._verbose:
                print(f"[JSON_STORE] 已清空用户 {user_id} 的记录")
        else:
            if self._records_dir.exists():
                shutil.rmtree(self._records_dir)
            self._records_dir.mkdir(parents=True, exist_ok=True)
            self._index = {}
            self._save_index()
            
            if self._verbose:
                print("[JSON_STORE] 已清空所有记录")


class Mem0KnowledgeStore(KnowledgeStore):
    """
    基于 Mem0 的向量知识存储
    
    支持：
    - 通义千问（Qwen）作为 LLM 和 Embedding
    - 豆包（Doubao）通过 litellm 作为 LLM（需要单独配置 embedding）
    - Qdrant 作为向量数据库（本地持久化）
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, verbose: bool = False):
        self._verbose = verbose
        self._enabled = False
        self._memory = None
        
        config = config or {}
        
        # 从配置或环境变量获取 API Key
        llm_provider = config.get("llm_provider", "qwen")  # qwen 或 doubao
        
        if llm_provider == "qwen":
            api_key = config.get("api_key") or os.getenv("QWEN_API_KEY")
            base_url = config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            llm_model = config.get("llm_model", "qwen-turbo")
            embedding_model = config.get("embedding_model", "text-embedding-v3")
            embedding_dims = config.get("embedding_dims", 1024)
        elif llm_provider == "doubao":
            # 豆包作为 LLM，但仍需要通义千问的 embedding
            api_key = config.get("api_key") or os.getenv("ARK_API_KEY")
            base_url = config.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")
            llm_model = config.get("llm_model", "doubao-seed-1-6-251015")
            # 豆包没有 embedding API，需要使用通义千问
            qwen_api_key = config.get("qwen_api_key") or os.getenv("QWEN_API_KEY")
            embedding_model = "text-embedding-v3"
            embedding_dims = 1024
        else:
            if self._verbose:
                print(f"[MEM0_STORE] 不支持的 LLM 提供者: {llm_provider}")
            return
        
        if not api_key:
            if self._verbose:
                print(f"[MEM0_STORE] 未找到 API Key ({llm_provider})")
            return
        
        try:
            from mem0 import Memory
            
            # 存储路径
            del_agent_root = Path(__file__).resolve().parents[1]
            qdrant_path = del_agent_root / "data" / "qdrant"
            qdrant_path.mkdir(parents=True, exist_ok=True)
            
            # 构建 Mem0 配置
            mem0_config = {
                "llm": {
                    "provider": "openai",  # 使用 OpenAI 兼容接口
                    "config": {
                        "model": llm_model,
                        "api_key": api_key,
                        "openai_base_url": base_url
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": embedding_model,
                        "api_key": qwen_api_key if llm_provider == "doubao" else api_key,
                        "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                        "embedding_dims": embedding_dims
                    }
                },
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": config.get("collection_name", "del_agent_knowledge"),
                        "path": str(qdrant_path),
                        "embedding_model_dims": embedding_dims,
                        "on_disk": True
                    }
                }
            }
            
            self._memory = Memory.from_config(mem0_config)
            self._enabled = True
            self._qdrant_path = qdrant_path
            
            if self._verbose:
                print(f"[MEM0_STORE] 初始化成功 (LLM: {llm_provider}, Qdrant: {qdrant_path})")
                
        except ImportError:
            if self._verbose:
                print("[MEM0_STORE] mem0ai 未安装，请运行: pip install mem0ai")
        except Exception as e:
            if self._verbose:
                print(f"[MEM0_STORE] 初始化失败: {e}")
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @property
    def backend_name(self) -> str:
        return "mem0"
    
    def insert(
        self,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        kind: str = "fact"
    ) -> bool:
        if not self._enabled:
            return False
        
        try:
            add_kwargs = {"user_id": user_id}
            if metadata:
                add_kwargs["metadata"] = metadata
            
            self._memory.add(content, **add_kwargs)
            
            if self._verbose:
                print(f"[MEM0_STORE] 插入成功 (user_id={user_id})")
            
            return True
        except Exception as e:
            if self._verbose:
                print(f"[MEM0_STORE] 插入失败: {e}")
            return False
    
    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeRecord]:
        if not self._enabled:
            return []
        
        try:
            results = self._memory.search(
                query=query,
                user_id=user_id or "default",
                limit=limit
            )
            
            records = []
            for item in results.get("results", []):
                content = item.get("memory", "")
                if content:
                    records.append(KnowledgeRecord(
                        id=item.get("id", ""),
                        content=content,
                        metadata=item.get("metadata"),
                        score=item.get("score", 0.0)
                    ))
            
            return records
        except Exception as e:
            if self._verbose:
                print(f"[MEM0_STORE] 搜索失败: {e}")
            return []
    
    def get_all(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[KnowledgeRecord]:
        if not self._enabled:
            return []
        
        try:
            results = self._memory.get_all(user_id=user_id or "default")
            
            records = []
            for item in results.get("results", [])[:limit]:
                content = item.get("memory", "")
                if content:
                    records.append(KnowledgeRecord(
                        id=item.get("id", ""),
                        content=content,
                        metadata=item.get("metadata")
                    ))
            
            return records
        except Exception as e:
            if self._verbose:
                print(f"[MEM0_STORE] 获取失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "backend": "mem0",
            "enabled": self._enabled,
            "storage_path": str(self._qdrant_path) if self._enabled else None,
            "total_records": 0
        }
        
        if self._enabled:
            try:
                # 尝试获取记录数
                results = self._memory.get_all(user_id="default")
                stats["total_records"] = len(results.get("results", []))
            except Exception:
                pass
        
        return stats
    
    def clear(self, user_id: Optional[str] = None) -> None:
        if not self._enabled:
            return
        
        try:
            memories = self._memory.get_all(user_id=user_id or "default")
            for mem in memories.get("results", []):
                self._memory.delete(memory_id=mem["id"])
            
            if self._verbose:
                print(f"[MEM0_STORE] 已清空 user_id={user_id or 'default'}")
        except Exception as e:
            if self._verbose:
                print(f"[MEM0_STORE] 清空失败: {e}")
    
    def close(self) -> None:
        if not self._enabled:
            return
        
        try:
            if hasattr(self._memory, 'vector_store') and hasattr(self._memory.vector_store, 'client'):
                client = self._memory.vector_store.client
                if hasattr(client, 'close'):
                    client.close()
                    if self._verbose:
                        print("[MEM0_STORE] 已关闭 Qdrant 连接")
        except Exception:
            pass


class HybridKnowledgeStore(KnowledgeStore):
    """
    混合存储：同时写入 Mem0 和 JSON，优先从 Mem0 读取
    
    适用于需要语义搜索但又想保留本地备份的场景
    """
    
    def __init__(
        self,
        mem0_config: Optional[Dict[str, Any]] = None,
        json_base_dir: Optional[str] = None,
        verbose: bool = False
    ):
        self._verbose = verbose
        self._mem0_store = Mem0KnowledgeStore(config=mem0_config, verbose=verbose)
        self._json_store = JsonKnowledgeStore(base_dir=json_base_dir, verbose=verbose)
        
        if self._verbose:
            print(f"[HYBRID_STORE] Mem0 enabled: {self._mem0_store.enabled}")
            print(f"[HYBRID_STORE] JSON enabled: {self._json_store.enabled}")
    
    @property
    def enabled(self) -> bool:
        return self._mem0_store.enabled or self._json_store.enabled
    
    @property
    def backend_name(self) -> str:
        if self._mem0_store.enabled:
            return "hybrid(mem0+json)"
        return "json"
    
    def insert(
        self,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        kind: str = "fact"
    ) -> bool:
        # 同时写入两个存储
        json_ok = self._json_store.insert(content, user_id, metadata, kind)
        mem0_ok = self._mem0_store.insert(content, user_id, metadata, kind) if self._mem0_store.enabled else False
        
        return json_ok or mem0_ok
    
    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeRecord]:
        # 优先使用 Mem0 的语义搜索
        if self._mem0_store.enabled:
            results = self._mem0_store.search(query, user_id, limit)
            if results:
                return results
        
        # 降级到 JSON 的关键词搜索
        return self._json_store.search(query, user_id, limit)
    
    def get_all(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[KnowledgeRecord]:
        # 从 JSON 获取（更可靠）
        return self._json_store.get_all(user_id, limit)
    
    def get_stats(self) -> Dict[str, Any]:
        json_stats = self._json_store.get_stats()
        mem0_stats = self._mem0_store.get_stats() if self._mem0_store.enabled else {}
        
        return {
            "backend": self.backend_name,
            "json": json_stats,
            "mem0": mem0_stats
        }
    
    def clear(self, user_id: Optional[str] = None) -> None:
        self._json_store.clear(user_id)
        if self._mem0_store.enabled:
            self._mem0_store.clear(user_id)
    
    def close(self) -> None:
        if self._mem0_store.enabled:
            self._mem0_store.close()


def create_knowledge_store(
    backend: str = "json",
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> KnowledgeStore:
    """
    创建知识存储实例
    
    Args:
        backend: 存储后端 ("json", "mem0", "hybrid")
        config: 配置字典
        verbose: 是否输出详细信息
    
    Returns:
        KnowledgeStore 实例
    
    Examples:
        # 创建 JSON 存储（默认）
        store = create_knowledge_store("json")
        
        # 创建 Mem0 存储（使用通义千问）
        store = create_knowledge_store("mem0", config={
            "llm_provider": "qwen",
            "api_key": "sk-xxx"
        })
        
        # 创建 Mem0 存储（使用豆包 LLM + 通义千问 Embedding）
        store = create_knowledge_store("mem0", config={
            "llm_provider": "doubao",
            "api_key": "ark-xxx",
            "qwen_api_key": "sk-xxx"  # embedding 用
        })
        
        # 创建混合存储
        store = create_knowledge_store("hybrid", config={...})
    """
    config = config or {}
    
    if backend == "json":
        return JsonKnowledgeStore(
            base_dir=config.get("base_dir"),
            verbose=verbose
        )
    
    elif backend == "mem0":
        store = Mem0KnowledgeStore(config=config, verbose=verbose)
        if not store.enabled:
            if verbose:
                print("[WARNING] Mem0 初始化失败，降级到 JSON 存储")
            return JsonKnowledgeStore(verbose=verbose)
        return store
    
    elif backend == "hybrid":
        return HybridKnowledgeStore(
            mem0_config=config,
            json_base_dir=config.get("json_base_dir"),
            verbose=verbose
        )
    
    else:
        raise ValueError(f"不支持的存储后端: {backend}")
