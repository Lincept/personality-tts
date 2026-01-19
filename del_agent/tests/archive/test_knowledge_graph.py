"""
测试知识图谱功能
"""

import pytest
from del_agent.storage.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelation,
    NodeType,
    RelationType,
    create_knowledge_graph
)


class TestKnowledgeNode:
    """测试知识节点"""
    
    def test_node_creation(self):
        """测试节点创建"""
        node = KnowledgeNode(
            id="node1",
            name="Python",
            node_type=NodeType.CONCEPT,
            properties={"category": "programming"}
        )
        
        assert node.id == "node1"
        assert node.name == "Python"
        assert node.node_type == NodeType.CONCEPT
        assert node.properties["category"] == "programming"
    
    def test_node_defaults(self):
        """测试节点默认值"""
        node = KnowledgeNode(
            id=None,
            name="Test",
            node_type=NodeType.ENTITY
        )
        
        assert node.properties == {}


class TestKnowledgeRelation:
    """测试知识关系"""
    
    def test_relation_creation(self):
        """测试关系创建"""
        relation = KnowledgeRelation(
            source_id="node1",
            target_id="node2",
            relation_type=RelationType.IS_A,
            properties={"strength": 0.9}
        )
        
        assert relation.source_id == "node1"
        assert relation.target_id == "node2"
        assert relation.relation_type == RelationType.IS_A
        assert relation.properties["strength"] == 0.9
    
    def test_relation_defaults(self):
        """测试关系默认值"""
        relation = KnowledgeRelation(
            source_id="src",
            target_id="tgt",
            relation_type=RelationType.HAS
        )
        
        assert relation.properties == {}


class TestNodeType:
    """测试节点类型枚举"""
    
    def test_node_types(self):
        """测试所有节点类型"""
        assert NodeType.CONCEPT.value == "concept"
        assert NodeType.ENTITY.value == "entity"
        assert NodeType.EVENT.value == "event"
        assert NodeType.ATTRIBUTE.value == "attribute"
        assert NodeType.OTHER.value == "other"


class TestRelationType:
    """测试关系类型枚举"""
    
    def test_relation_types(self):
        """测试所有关系类型"""
        assert RelationType.IS_A.value == "is_a"
        assert RelationType.HAS.value == "has"
        assert RelationType.RELATES_TO.value == "relates_to"
        assert RelationType.CAUSED_BY.value == "caused_by"
        assert RelationType.LEADS_TO.value == "leads_to"
        assert RelationType.SIMILAR_TO.value == "similar_to"
        assert RelationType.PART_OF.value == "part_of"
        assert RelationType.OTHER.value == "other"


class TestKnowledgeGraph:
    """测试知识图谱类"""
    
    def test_graph_disabled(self):
        """测试未启用时的行为"""
        graph = KnowledgeGraph(mem0_manager=None)
        
        assert not graph.enabled
        assert graph.add_node("test", NodeType.CONCEPT) is None
        assert not graph.add_relation("src", "tgt", RelationType.HAS)
        assert graph.query_nodes() == []
        assert graph.query_relations() == []
    
    def test_graph_without_graph_support(self):
        """测试 Mem0 未启用图谱功能"""
        class MockMem0Manager:
            enabled = True
            enable_graph = False
        
        graph = KnowledgeGraph(mem0_manager=MockMem0Manager())
        assert not graph.enabled
    
    def test_graph_with_graph_support(self):
        """测试 Mem0 启用图谱功能"""
        class MockMem0Manager:
            enabled = True
            enable_graph = True
            saved_items = []
            
            def save(self, memory, user_id, kind, metadata):
                self.saved_items.append({
                    'memory': memory,
                    'user_id': user_id,
                    'kind': kind,
                    'metadata': metadata
                })
        
        mock_manager = MockMem0Manager()
        graph = KnowledgeGraph(mem0_manager=mock_manager)
        
        assert graph.enabled
        
        # 测试添加节点
        node_id = graph.add_node(
            name="Python",
            node_type=NodeType.CONCEPT,
            properties={"category": "language"}
        )
        
        assert node_id == "Python"
        assert len(mock_manager.saved_items) == 1
        assert mock_manager.saved_items[0]['kind'] == "relationship"
    
    def test_add_relation(self):
        """测试添加关系"""
        class MockMem0Manager:
            enabled = True
            enable_graph = True
            saved_items = []
            
            def save(self, memory, user_id, kind, metadata):
                self.saved_items.append({
                    'memory': memory,
                    'metadata': metadata
                })
        
        mock_manager = MockMem0Manager()
        graph = KnowledgeGraph(mem0_manager=mock_manager)
        
        success = graph.add_relation(
            source_name="Python",
            target_name="Programming",
            relation_type=RelationType.IS_A
        )
        
        assert success
        assert len(mock_manager.saved_items) == 1
        assert "is_a" in mock_manager.saved_items[0]['memory']
    
    def test_query_nodes(self):
        """测试查询节点"""
        class MockMem0Manager:
            enabled = True
            enable_graph = True
            
            def search(self, query, user_id, limit):
                from del_agent.memory.store import MemoryRecord
                return [
                    MemoryRecord(
                        content="Python",
                        id="node1",
                        metadata={
                            'name': 'Python',
                            'node_type': 'concept'
                        }
                    )
                ]
        
        graph = KnowledgeGraph(mem0_manager=MockMem0Manager())
        nodes = graph.query_nodes(node_type=NodeType.CONCEPT)
        
        assert len(nodes) == 1
        assert nodes[0].name == "Python"
        assert nodes[0].node_type == NodeType.CONCEPT
    
    def test_query_relations(self):
        """测试查询关系"""
        class MockMem0Manager:
            enabled = True
            enable_graph = True
            
            def search(self, query, user_id, limit):
                from del_agent.memory.store import MemoryRecord
                return [
                    MemoryRecord(
                        content="Python is_a Programming",
                        id="rel1",
                        metadata={
                            'source': 'Python',
                            'target': 'Programming',
                            'relation_type': 'is_a'
                        }
                    )
                ]
        
        graph = KnowledgeGraph(mem0_manager=MockMem0Manager())
        relations = graph.query_relations(
            source_name="Python",
            relation_type=RelationType.IS_A
        )
        
        assert len(relations) == 1
        assert relations[0].source_id == "Python"
        assert relations[0].target_id == "Programming"
        assert relations[0].relation_type == RelationType.IS_A
    
    def test_find_path(self):
        """测试路径查找"""
        class MockMem0Manager:
            enabled = True
            enable_graph = True
            
            def search(self, query, user_id, limit):
                from del_agent.memory.store import MemoryRecord
                return [
                    MemoryRecord(content="path found", id="path1")
                ]
        
        graph = KnowledgeGraph(mem0_manager=MockMem0Manager())
        paths = graph.find_path("Python", "Language")
        
        # 简化实现，返回直接路径
        assert len(paths) == 1
        assert paths[0] == ["Python", "Language"]
    
    def test_cluster_query(self):
        """测试聚类查询"""
        class MockMem0Manager:
            enabled = True
            enable_graph = True
            
            def search(self, query, user_id, limit):
                from del_agent.memory.store import MemoryRecord
                return [
                    MemoryRecord(
                        content="Python",
                        id="node1",
                        metadata={'name': 'Python', 'node_type': 'concept'}
                    ),
                    MemoryRecord(
                        content="relation",
                        id="rel1",
                        metadata={
                            'source': 'Python',
                            'target': 'Language',
                            'relation_type': 'is_a'
                        }
                    )
                ]
        
        graph = KnowledgeGraph(mem0_manager=MockMem0Manager())
        result = graph.cluster_query("Python", depth=2)
        
        assert result['center'] == "Python"
        assert len(result['nodes']) == 1
        assert len(result['relations']) == 1


class TestKnowledgeGraphIntegration:
    """集成测试（需要真实配置）"""
    
    def test_create_from_config_without_graph(self):
        """测试从配置创建（未启用图谱）"""
        config = {
            'enable_mem0': False,
            'enable_graph': False
        }
        
        graph = create_knowledge_graph(config)
        assert not graph.enabled
    
    @pytest.mark.skip(reason="需要真实 Mem0 + Neo4j 配置")
    def test_create_from_config_with_graph(self):
        """测试从配置创建（启用图谱）"""
        config = {
            'enable_mem0': True,
            'enable_graph': True,
            'llm_api_key': 'test_key',
            'llm_base_url': 'http://test.com',
            'llm_model': 'test-model',
            'neo4j_url': 'bolt://localhost:7687',
            'neo4j_username': 'neo4j',
            'neo4j_password': 'password'
        }
        
        graph = create_knowledge_graph(config)
        # 实际测试需要真实配置
        assert graph is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
