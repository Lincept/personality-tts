"""
词典存储框架 (Dictionary Store Framework)

提供统一的词典管理接口，支持多种存储后端：
1. JSON 文件存储（简单、轻量）
2. Mem0 记忆存储（语义检索、持久化）
3. 可扩展其他后端

作者：AI Data Factory
创建日期：2026-01-19
版本：2.2.1
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import json
import logging
from pathlib import Path


class DictionaryStore(ABC):
    """词典存储抽象接口
    
    定义统一的词典操作方法，具体实现由子类完成。
    设计原则：简单、可扩展、向后兼容
    """
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> Dict[str, str]:
        """搜索词典
        
        Args:
            query: 搜索查询（可以是关键词或语义查询）
            limit: 返回结果数量限制
            
        Returns:
            Dict[str, str]: {词条: 解释} 的字典
        """
        pass
    
    @abstractmethod
    def add(self, term: str, meaning: str, metadata: Optional[Dict[str, Any]] = None):
        """添加单个词条
        
        Args:
            term: 词条（黑话）
            meaning: 解释
            metadata: 元数据（可选）
        """
        pass
    
    @abstractmethod
    def update(self, terms: Dict[str, str]):
        """批量更新词条
        
        Args:
            terms: {词条: 解释} 的字典
        """
        pass
    
    @abstractmethod
    def get(self, term: str) -> Optional[str]:
        """获取单个词条的解释
        
        Args:
            term: 词条
            
        Returns:
            Optional[str]: 解释，不存在则返回 None
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, str]:
        """获取所有词条
        
        Returns:
            Dict[str, str]: 完整词典
        """
        pass
    
    @abstractmethod
    def delete(self, term: str) -> bool:
        """删除词条
        
        Args:
            term: 要删除的词条
            
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    def clear(self):
        """清空词典"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取词典统计信息
        
        Returns:
            Dict: 统计信息（词条数量、大小等）
        """
        pass


class JSONDictionaryStore(DictionaryStore):
    """基于 JSON 文件的词典存储
    
    特点：
    - 简单、轻量、无外部依赖
    - 适合小规模词典（< 10000 条）
    - 支持自动保存
    """
    
    def __init__(
        self,
        file_path: Optional[Path] = None,
        auto_save: bool = True
    ):
        """
        初始化 JSON 词典存储
        
        Args:
            file_path: JSON 文件路径
            auto_save: 是否自动保存
        """
        self.file_path = file_path
        self.auto_save = auto_save
        self.dictionary: Dict[str, str] = {}
        self.logger = logging.getLogger(f"{__name__}.JSONDictionaryStore")
        
        # 加载现有词典
        if self.file_path and self.file_path.exists():
            self._load()
        
        self.logger.info(
            f"JSONDictionaryStore initialized with {len(self.dictionary)} terms"
        )
    
    def _load(self):
        """从文件加载词典"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.dictionary = json.load(f)
            self.logger.info(f"Loaded {len(self.dictionary)} terms from {self.file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load dictionary: {e}")
            self.dictionary = {}
    
    def _save(self):
        """保存词典到文件"""
        if not self.file_path:
            return
        
        try:
            # 确保目录存在
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    self.dictionary,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            self.logger.debug(f"Saved {len(self.dictionary)} terms to {self.file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save dictionary: {e}")
    
    def search(self, query: str, limit: int = 5) -> Dict[str, str]:
        """搜索词典（简单字符串匹配）
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            Dict[str, str]: 匹配的词条
        """
        query_lower = query.lower()
        results = {}
        
        for term, meaning in self.dictionary.items():
            if query_lower in term.lower() or query_lower in meaning.lower():
                results[term] = meaning
                if len(results) >= limit:
                    break
        
        return results
    
    def add(self, term: str, meaning: str, metadata: Optional[Dict[str, Any]] = None):
        """添加词条"""
        self.dictionary[term] = meaning
        
        if self.auto_save:
            self._save()
        
        self.logger.debug(f"Added term: {term}")
    
    def update(self, terms: Dict[str, str]):
        """批量更新词条"""
        before_count = len(self.dictionary)
        self.dictionary.update(terms)
        after_count = len(self.dictionary)
        
        if self.auto_save:
            self._save()
        
        self.logger.info(f"Updated dictionary: {after_count - before_count} new terms")
    
    def get(self, term: str) -> Optional[str]:
        """获取词条解释"""
        return self.dictionary.get(term)
    
    def get_all(self) -> Dict[str, str]:
        """获取所有词条"""
        return self.dictionary.copy()
    
    def delete(self, term: str) -> bool:
        """删除词条"""
        if term in self.dictionary:
            del self.dictionary[term]
            
            if self.auto_save:
                self._save()
            
            self.logger.debug(f"Deleted term: {term}")
            return True
        return False
    
    def clear(self):
        """清空词典"""
        self.dictionary.clear()
        
        if self.auto_save:
            self._save()
        
        self.logger.info("Dictionary cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "backend": "json",
            "total_terms": len(self.dictionary),
            "file_path": str(self.file_path) if self.file_path else None
        }


class Mem0DictionaryStore(DictionaryStore):
    """基于 Mem0 的词典存储
    
    特点：
    - 语义检索能力
    - 持久化存储（Qdrant）
    - 适合大规模词典
    - 支持元数据和关系
    """
    
    def __init__(
        self,
        mem0_config: Dict[str, Any],
        user_id: str = "slang_dictionary",
        collection_prefix: str = "slang"
    ):
        """
        初始化 Mem0 词典存储
        
        Args:
            mem0_config: Mem0 配置字典
            user_id: 用户 ID（用于隔离不同词典）
            collection_prefix: 集合名称前缀
        """
        self.logger = logging.getLogger(f"{__name__}.Mem0DictionaryStore")
        
        # 导入 Mem0 管理器
        try:
            # 尝试从 del_agent.memory 导入
            try:
                from ..memory.mem0_manager import Mem0Manager
            except (ImportError, ValueError):
                # 如果失败，尝试从当前项目导入
                from memory.mem0_manager import Mem0Manager
            
            self.mem0_manager = Mem0Manager(mem0_config)
            self.user_id = user_id
            self.collection_prefix = collection_prefix
            
            if not self.mem0_manager.enabled:
                raise RuntimeError("Mem0 is not enabled")
            
            self.logger.info(f"Mem0DictionaryStore initialized for user: {user_id}")
            
        except ImportError as e:
            raise RuntimeError(f"Failed to import Mem0Manager: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Mem0: {e}")
    
    def search(self, query: str, limit: int = 5) -> Dict[str, str]:
        """语义搜索词典
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            Dict[str, str]: 匹配的词条
        """
        try:
            # 使用 Mem0 的语义搜索
            records = self.mem0_manager.search(
                query=query,
                user_id=self.user_id,
                limit=limit
            )
            
            # 解析记忆内容为词条
            results = {}
            for record in records:
                content = record.content
                # 期望格式: "term: meaning" 或 "term -> meaning"
                if ':' in content:
                    parts = content.split(':', 1)
                    term = parts[0].strip()
                    meaning = parts[1].strip()
                    results[term] = meaning
                elif '->' in content:
                    parts = content.split('->', 1)
                    term = parts[0].strip()
                    meaning = parts[1].strip()
                    results[term] = meaning
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return {}
    
    def add(self, term: str, meaning: str, metadata: Optional[Dict[str, Any]] = None):
        """添加词条到 Mem0"""
        try:
            # 格式化为 "term: meaning"
            memory_content = f"{term}: {meaning}"
            
            self.mem0_manager.save(
                memory=memory_content,
                user_id=self.user_id,
                kind="fact",
                metadata=metadata or {"type": "slang_term"}
            )
            
            self.logger.debug(f"Added term to Mem0: {term}")
            
        except Exception as e:
            self.logger.error(f"Failed to add term: {e}")
    
    def update(self, terms: Dict[str, str]):
        """批量更新词条"""
        for term, meaning in terms.items():
            self.add(term, meaning)
        
        self.logger.info(f"Updated {len(terms)} terms in Mem0")
    
    def get(self, term: str) -> Optional[str]:
        """获取词条（通过搜索）"""
        results = self.search(term, limit=1)
        return results.get(term)
    
    def get_all(self) -> Dict[str, str]:
        """获取所有词条"""
        try:
            all_memories = self.mem0_manager.get_all(user_id=self.user_id)
            
            results = {}
            for mem in all_memories:
                content = mem.get("memory", "")
                if ':' in content:
                    parts = content.split(':', 1)
                    term = parts[0].strip()
                    meaning = parts[1].strip()
                    results[term] = meaning
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to get all terms: {e}")
            return {}
    
    def delete(self, term: str) -> bool:
        """删除词条（通过搜索和删除）"""
        try:
            # 搜索词条
            records = self.mem0_manager.search(
                query=term,
                user_id=self.user_id,
                limit=1
            )
            
            if records and records[0].id:
                # 删除记忆
                self.mem0_manager.memory.delete(memory_id=records[0].id)
                self.logger.debug(f"Deleted term: {term}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete term: {e}")
            return False
    
    def clear(self):
        """清空词典"""
        try:
            self.mem0_manager.clear(user_id=self.user_id)
            self.logger.info("Dictionary cleared in Mem0")
        except Exception as e:
            self.logger.error(f"Failed to clear dictionary: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        all_terms = self.get_all()
        return {
            "backend": "mem0",
            "total_terms": len(all_terms),
            "user_id": self.user_id,
            "collection_prefix": self.collection_prefix
        }


def create_dictionary_store(config: Optional[Dict[str, Any]] = None) -> DictionaryStore:
    """词典存储工厂方法
    
    根据配置创建相应的词典存储实例。
    
    Args:
        config: 配置字典，包含：
            - backend: 存储后端类型 ("json" 或 "mem0")
            - file_path: JSON 文件路径（backend=json 时）
            - auto_save: 是否自动保存（backend=json 时）
            - mem0_config: Mem0 配置（backend=mem0 时）
            - user_id: 用户 ID（backend=mem0 时）
    
    Returns:
        DictionaryStore: 词典存储实例
    
    Example:
        >>> # JSON 存储
        >>> store = create_dictionary_store({
        ...     "backend": "json",
        ...     "file_path": "data/slang_dict.json",
        ...     "auto_save": True
        ... })
        
        >>> # Mem0 存储
        >>> store = create_dictionary_store({
        ...     "backend": "mem0",
        ...     "mem0_config": {
        ...         "enable_mem0": True,
        ...         "llm_api_key": "...",
        ...         "llm_base_url": "...",
        ...         "llm_model": "qwen-turbo"
        ...     },
        ...     "user_id": "slang_dictionary"
        ... })
    """
    if config is None:
        config = {}
    
    backend = config.get("backend", "json").lower()
    
    if backend == "mem0":
        mem0_config = config.get("mem0_config", {})
        user_id = config.get("user_id", "slang_dictionary")
        collection_prefix = config.get("collection_prefix", "slang")
        
        return Mem0DictionaryStore(
            mem0_config=mem0_config,
            user_id=user_id,
            collection_prefix=collection_prefix
        )
    
    else:  # 默认使用 JSON
        file_path = config.get("file_path")
        if file_path and not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        auto_save = config.get("auto_save", True)
        
        return JSONDictionaryStore(
            file_path=file_path,
            auto_save=auto_save
        )
