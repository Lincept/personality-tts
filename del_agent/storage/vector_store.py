"""
向量存储接口 - RAG 检索对接层

通过 Mem0 实现向量检索和存储功能
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    """向量检索记录"""
    content: str
    score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class VectorStore:
    """
    向量存储接口
    
    功能：
    - 向量检索（RAG）
    - 向量插入（知识更新）
    - 基于 Mem0 的向量数据库实现
    """
    
    def __init__(self, mem0_manager=None):
        """
        初始化向量存储
        
        Args:
            mem0_manager: Mem0Manager 实例（来自 del_agent.memory）
        """
        self.mem0_manager = mem0_manager
        self.enabled = bool(mem0_manager and mem0_manager.enabled)
        
        if self.enabled:
            logger.info("向量存储已启用（基于 Mem0）")
        else:
            logger.warning("向量存储未启用")
    
    def search(
        self,
        query: str,
        user_id: str = "default",
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorRecord]:
        """
        向量检索（语义搜索）
        
        Args:
            query: 查询文本
            user_id: 用户 ID
            limit: 返回结果数量
            filters: 过滤条件（可选）
        
        Returns:
            检索结果列表
        """
        if not self.enabled:
            logger.debug("向量存储未启用，返回空结果")
            return []
        
        try:
            # 调用 Mem0 的 search 接口
            memory_records = self.mem0_manager.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            # 转换为 VectorRecord
            results = []
            for record in memory_records:
                results.append(
                    VectorRecord(
                        content=record.content,
                        score=1.0,  # Mem0 不返回 score，默认为 1.0
                        metadata=record.metadata,
                        id=record.id
                    )
                )
            
            logger.info(f"向量检索: query='{query}', 结果数={len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}", exc_info=True)
            return []
    
    def insert(
        self,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        kind: str = "fact"
    ) -> bool:
        """
        插入向量记录
        
        Args:
            content: 内容文本
            user_id: 用户 ID
            metadata: 元数据
            kind: 记忆类型（fact/relationship/other）
        
        Returns:
            是否成功
        """
        if not self.enabled:
            logger.debug("向量存储未启用，跳过插入")
            return False
        
        try:
            # 调用 Mem0 的 save 接口
            self.mem0_manager.save(
                memory=content,
                user_id=user_id,
                kind=kind,
                metadata=metadata
            )
            
            logger.info(f"向量插入成功: user_id={user_id}, kind={kind}")
            return True
            
        except Exception as e:
            logger.error(f"向量插入失败: {e}", exc_info=True)
            return False
    
    def batch_insert(
        self,
        contents: List[str],
        user_id: str = "default",
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        kind: str = "fact"
    ) -> int:
        """
        批量插入向量记录
        
        Args:
            contents: 内容列表
            user_id: 用户 ID
            metadata_list: 元数据列表
            kind: 记忆类型
        
        Returns:
            成功插入的数量
        """
        if not self.enabled:
            return 0
        
        success_count = 0
        metadata_list = metadata_list or [None] * len(contents)
        
        for i, content in enumerate(contents):
            metadata = metadata_list[i] if i < len(metadata_list) else None
            if self.insert(content, user_id, metadata, kind):
                success_count += 1
        
        logger.info(f"批量插入: 总数={len(contents)}, 成功={success_count}")
        return success_count
    
    def delete(self, record_id: str, user_id: str = "default") -> bool:
        """
        删除向量记录
        
        Args:
            record_id: 记录 ID
            user_id: 用户 ID
        
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        try:
            # Mem0 的删除接口（如果支持）
            # 注意：当前 Mem0Manager 可能没有直接的删除接口
            logger.warning("向量删除功能暂未实现")
            return False
            
        except Exception as e:
            logger.error(f"向量删除失败: {e}", exc_info=True)
            return False
    
    def clear(self, user_id: str = "default") -> bool:
        """
        清空用户的所有向量记录
        
        Args:
            user_id: 用户 ID
        
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        try:
            # 调用 Mem0 的清空接口
            if hasattr(self.mem0_manager, 'clear'):
                self.mem0_manager.clear(user_id)
                logger.info(f"已清空用户 {user_id} 的向量记录")
                return True
            else:
                logger.warning("Mem0Manager 没有 clear 方法")
                return False
                
        except Exception as e:
            logger.error(f"清空向量记录失败: {e}", exc_info=True)
            return False
    
    def get_all(self, user_id: str = "default") -> List[VectorRecord]:
        """
        获取用户的所有向量记录
        
        Args:
            user_id: 用户 ID
        
        Returns:
            所有记录列表
        """
        if not self.enabled:
            return []
        
        try:
            # 调用 Mem0 的获取所有记录接口
            if hasattr(self.mem0_manager, 'get_all'):
                records = self.mem0_manager.get_all(user_id)
                # 转换为 VectorRecord
                results = []
                for r in records:
                    results.append(
                        VectorRecord(
                            content=r.get('content', r.get('memory', '')),
                            metadata=r.get('metadata'),
                            id=r.get('id')
                        )
                    )
                return results
            else:
                logger.warning("Mem0Manager 没有 get_all 方法")
                return []
                
        except Exception as e:
            logger.error(f"获取所有记录失败: {e}", exc_info=True)
            return []
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> 'VectorStore':
        """
        从配置创建向量存储实例
        
        Args:
            config: 配置字典
        
        Returns:
            VectorStore 实例
        """
        from ..memory.factory import create_memory_manager
        
        # 创建 Mem0Manager
        mem0_manager = create_memory_manager(config)
        
        # 创建 VectorStore
        return VectorStore(mem0_manager)


# 便捷函数
def create_vector_store(config: Dict[str, Any]) -> VectorStore:
    """
    创建向量存储实例（便捷函数）
    
    Args:
        config: 配置字典
    
    Returns:
        VectorStore 实例
    """
    return VectorStore.create_from_config(config)
