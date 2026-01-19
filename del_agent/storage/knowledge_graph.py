"""
知识图谱接口 - 结构化知识存储

通过 Mem0 的图谱功能实现知识节点和关系管理
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """知识节点类型"""
    CONCEPT = "concept"          # 概念
    ENTITY = "entity"            # 实体
    EVENT = "event"              # 事件
    ATTRIBUTE = "attribute"      # 属性
    OTHER = "other"              # 其他


class RelationType(Enum):
    """关系类型"""
    IS_A = "is_a"                # 是一个
    HAS = "has"                  # 拥有
    RELATES_TO = "relates_to"    # 关联
    CAUSED_BY = "caused_by"      # 由...引起
    LEADS_TO = "leads_to"        # 导致
    SIMILAR_TO = "similar_to"    # 相似于
    PART_OF = "part_of"          # 是...的一部分
    OTHER = "other"              # 其他


@dataclass
class KnowledgeNode:
    """知识节点"""
    id: Optional[str]
    name: str
    node_type: NodeType
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class KnowledgeRelation:
    """知识关系"""
    source_id: str
    target_id: str
    relation_type: RelationType
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class KnowledgeGraph:
    """
    知识图谱接口
    
    功能：
    - 节点管理（创建、查询、更新、删除）
    - 关系管理（创建、查询、删除）
    - 图谱查询（路径查询、聚类查询）
    - 基于 Mem0 的图谱功能实现
    """
    
    def __init__(self, mem0_manager=None):
        """
        初始化知识图谱
        
        Args:
            mem0_manager: Mem0Manager 实例（必须启用图谱功能）
        """
        self.mem0_manager = mem0_manager
        self.enabled = bool(
            mem0_manager and 
            mem0_manager.enabled and 
            mem0_manager.enable_graph
        )
        
        if self.enabled:
            logger.info("知识图谱已启用（基于 Mem0 + Neo4j）")
        else:
            logger.warning("知识图谱未启用（需要 enable_graph=True）")
    
    def add_node(
        self,
        name: str,
        node_type: NodeType,
        properties: Optional[Dict[str, Any]] = None,
        user_id: str = "default"
    ) -> Optional[str]:
        """
        添加知识节点
        
        Args:
            name: 节点名称
            node_type: 节点类型
            properties: 节点属性
            user_id: 用户 ID
        
        Returns:
            节点 ID（如果成功）
        """
        if not self.enabled:
            logger.debug("知识图谱未启用，跳过添加节点")
            return None
        
        try:
            # 构建节点内容
            properties = properties or {}
            properties['node_type'] = node_type.value
            properties['name'] = name
            
            # 使用 Mem0 的 save 接口（kind=relationship 会触发图谱抽取）
            content = f"知识节点: {name} (类型: {node_type.value})"
            self.mem0_manager.save(
                memory=content,
                user_id=user_id,
                kind="relationship",  # 触发图谱功能
                metadata=properties
            )
            
            logger.info(f"添加知识节点: name={name}, type={node_type.value}")
            return name  # Mem0 可能不返回 ID，使用 name 作为标识
            
        except Exception as e:
            logger.error(f"添加知识节点失败: {e}", exc_info=True)
            return None
    
    def add_relation(
        self,
        source_name: str,
        target_name: str,
        relation_type: RelationType,
        properties: Optional[Dict[str, Any]] = None,
        user_id: str = "default"
    ) -> bool:
        """
        添加知识关系
        
        Args:
            source_name: 源节点名称
            target_name: 目标节点名称
            relation_type: 关系类型
            properties: 关系属性
            user_id: 用户 ID
        
        Returns:
            是否成功
        """
        if not self.enabled:
            logger.debug("知识图谱未启用，跳过添加关系")
            return False
        
        try:
            # 构建关系内容
            properties = properties or {}
            properties['relation_type'] = relation_type.value
            properties['source'] = source_name
            properties['target'] = target_name
            
            # 使用 Mem0 的 save 接口
            content = f"{source_name} {relation_type.value} {target_name}"
            self.mem0_manager.save(
                memory=content,
                user_id=user_id,
                kind="relationship",
                metadata=properties
            )
            
            logger.info(f"添加知识关系: {source_name} -> {relation_type.value} -> {target_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加知识关系失败: {e}", exc_info=True)
            return False
    
    def query_nodes(
        self,
        node_type: Optional[NodeType] = None,
        name_pattern: Optional[str] = None,
        user_id: str = "default",
        limit: int = 10
    ) -> List[KnowledgeNode]:
        """
        查询知识节点
        
        Args:
            node_type: 节点类型过滤
            name_pattern: 名称模式匹配
            user_id: 用户 ID
            limit: 返回数量限制
        
        Returns:
            节点列表
        """
        if not self.enabled:
            return []
        
        try:
            # 构建查询
            query = ""
            if node_type:
                query += f"类型为 {node_type.value} 的"
            if name_pattern:
                query += f"名称包含 {name_pattern} 的"
            query += "知识节点"
            
            # 使用 Mem0 的 search 接口
            results = self.mem0_manager.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            # 转换为 KnowledgeNode
            nodes = []
            for record in results:
                metadata = record.metadata or {}
                node = KnowledgeNode(
                    id=record.id,
                    name=metadata.get('name', record.content),
                    node_type=NodeType(metadata.get('node_type', 'other')),
                    properties=metadata
                )
                nodes.append(node)
            
            logger.info(f"查询知识节点: 结果数={len(nodes)}")
            return nodes
            
        except Exception as e:
            logger.error(f"查询知识节点失败: {e}", exc_info=True)
            return []
    
    def query_relations(
        self,
        source_name: Optional[str] = None,
        target_name: Optional[str] = None,
        relation_type: Optional[RelationType] = None,
        user_id: str = "default",
        limit: int = 10
    ) -> List[KnowledgeRelation]:
        """
        查询知识关系
        
        Args:
            source_name: 源节点名称
            target_name: 目标节点名称
            relation_type: 关系类型
            user_id: 用户 ID
            limit: 返回数量限制
        
        Returns:
            关系列表
        """
        if not self.enabled:
            return []
        
        try:
            # 构建查询
            query_parts = []
            if source_name:
                query_parts.append(f"从 {source_name}")
            if relation_type:
                query_parts.append(relation_type.value)
            if target_name:
                query_parts.append(f"到 {target_name}")
            query = " ".join(query_parts) if query_parts else "知识关系"
            
            # 使用 Mem0 的 search 接口
            results = self.mem0_manager.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            # 转换为 KnowledgeRelation
            relations = []
            for record in results:
                metadata = record.metadata or {}
                if 'relation_type' in metadata:
                    relation = KnowledgeRelation(
                        source_id=metadata.get('source', ''),
                        target_id=metadata.get('target', ''),
                        relation_type=RelationType(metadata.get('relation_type', 'other')),
                        properties=metadata
                    )
                    relations.append(relation)
            
            logger.info(f"查询知识关系: 结果数={len(relations)}")
            return relations
            
        except Exception as e:
            logger.error(f"查询知识关系失败: {e}", exc_info=True)
            return []
    
    def find_path(
        self,
        source_name: str,
        target_name: str,
        max_depth: int = 3,
        user_id: str = "default"
    ) -> List[List[str]]:
        """
        查找两个节点之间的路径
        
        Args:
            source_name: 源节点
            target_name: 目标节点
            max_depth: 最大深度
            user_id: 用户 ID
        
        Returns:
            路径列表（每个路径是节点名称列表）
        """
        if not self.enabled:
            return []
        
        try:
            # 构建路径查询
            query = f"从 {source_name} 到 {target_name} 的关系路径"
            
            # 使用 Mem0 的 search 接口
            results = self.mem0_manager.search(
                query=query,
                user_id=user_id,
                limit=10
            )
            
            # 这里简化处理，实际需要更复杂的图遍历算法
            # Mem0 可能不直接支持路径查询，需要后期优化
            logger.warning("路径查询功能简化实现，可能不准确")
            
            # 返回简单路径
            if results:
                return [[source_name, target_name]]
            return []
            
        except Exception as e:
            logger.error(f"查找路径失败: {e}", exc_info=True)
            return []
    
    def cluster_query(
        self,
        center_name: str,
        depth: int = 2,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        聚类查询：查找以某个节点为中心的子图
        
        Args:
            center_name: 中心节点名称
            depth: 深度
            user_id: 用户 ID
        
        Returns:
            子图结构（节点和关系）
        """
        if not self.enabled:
            return {'nodes': [], 'relations': []}
        
        try:
            # 构建聚类查询
            query = f"与 {center_name} 相关的知识"
            
            # 使用 Mem0 的 search 接口
            results = self.mem0_manager.search(
                query=query,
                user_id=user_id,
                limit=20
            )
            
            # 提取节点和关系
            nodes = []
            relations = []
            
            for record in results:
                metadata = record.metadata or {}
                if 'node_type' in metadata:
                    node = KnowledgeNode(
                        id=record.id,
                        name=metadata.get('name', record.content),
                        node_type=NodeType(metadata.get('node_type', 'other')),
                        properties=metadata
                    )
                    nodes.append(node)
                elif 'relation_type' in metadata:
                    relation = KnowledgeRelation(
                        source_id=metadata.get('source', ''),
                        target_id=metadata.get('target', ''),
                        relation_type=RelationType(metadata.get('relation_type', 'other')),
                        properties=metadata
                    )
                    relations.append(relation)
            
            result = {
                'center': center_name,
                'nodes': nodes,
                'relations': relations,
                'depth': depth
            }
            
            logger.info(f"聚类查询: center={center_name}, nodes={len(nodes)}, relations={len(relations)}")
            return result
            
        except Exception as e:
            logger.error(f"聚类查询失败: {e}", exc_info=True)
            return {'nodes': [], 'relations': []}
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> 'KnowledgeGraph':
        """
        从配置创建知识图谱实例
        
        Args:
            config: 配置字典（需要 enable_graph=True）
        
        Returns:
            KnowledgeGraph 实例
        """
        from ..memory.factory import create_memory_manager
        
        # 创建 Mem0Manager（确保启用图谱）
        mem0_manager = create_memory_manager(config)
        
        # 创建 KnowledgeGraph
        return KnowledgeGraph(mem0_manager)


# 便捷函数
def create_knowledge_graph(config: Dict[str, Any]) -> KnowledgeGraph:
    """
    创建知识图谱实例（便捷函数）
    
    Args:
        config: 配置字典
    
    Returns:
        KnowledgeGraph 实例
    """
    return KnowledgeGraph.create_from_config(config)
