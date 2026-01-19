"""
测试向量存储功能
"""

import pytest
from del_agent.storage.vector_store import VectorStore, VectorRecord, create_vector_store


class TestVectorStore:
    """测试向量存储类"""
    
    def test_vector_store_disabled(self):
        """测试未启用时的行为"""
        store = VectorStore(mem0_manager=None)
        
        assert not store.enabled
        assert store.search("test query") == []
        assert not store.insert("test content")
        assert store.batch_insert(["content1", "content2"]) == 0
    
    def test_vector_record_creation(self):
        """测试 VectorRecord 创建"""
        record = VectorRecord(
            content="test content",
            score=0.95,
            metadata={"key": "value"},
            id="test_id"
        )
        
        assert record.content == "test content"
        assert record.score == 0.95
        assert record.metadata == {"key": "value"}
        assert record.id == "test_id"
    
    def test_vector_record_defaults(self):
        """测试 VectorRecord 默认值"""
        record = VectorRecord(content="test")
        
        assert record.content == "test"
        assert record.score == 0.0
        assert record.metadata is None
        assert record.id is None
    
    def test_search_with_mock_manager(self):
        """测试搜索功能（Mock）"""
        # 创建 Mock Mem0Manager
        class MockMem0Manager:
            enabled = True
            
            def search(self, query, user_id, limit):
                from del_agent.memory.store import MemoryRecord
                return [
                    MemoryRecord(
                        content="result 1",
                        id="id1",
                        metadata={"score": 0.9}
                    ),
                    MemoryRecord(
                        content="result 2",
                        id="id2",
                        metadata={"score": 0.8}
                    )
                ]
        
        store = VectorStore(mem0_manager=MockMem0Manager())
        results = store.search("test query", limit=2)
        
        assert len(results) == 2
        assert results[0].content == "result 1"
        assert results[1].content == "result 2"
    
    def test_insert_with_mock_manager(self):
        """测试插入功能（Mock）"""
        class MockMem0Manager:
            enabled = True
            saved_items = []
            
            def save(self, memory, user_id, kind, metadata):
                self.saved_items.append({
                    'memory': memory,
                    'user_id': user_id,
                    'kind': kind,
                    'metadata': metadata
                })
        
        mock_manager = MockMem0Manager()
        store = VectorStore(mem0_manager=mock_manager)
        
        success = store.insert(
            content="test content",
            user_id="user1",
            metadata={"key": "value"},
            kind="fact"
        )
        
        assert success
        assert len(mock_manager.saved_items) == 1
        assert mock_manager.saved_items[0]['memory'] == "test content"
        assert mock_manager.saved_items[0]['user_id'] == "user1"
        assert mock_manager.saved_items[0]['kind'] == "fact"
    
    def test_batch_insert(self):
        """测试批量插入"""
        class MockMem0Manager:
            enabled = True
            saved_items = []
            
            def save(self, memory, user_id, kind, metadata):
                self.saved_items.append(memory)
        
        mock_manager = MockMem0Manager()
        store = VectorStore(mem0_manager=mock_manager)
        
        count = store.batch_insert(
            contents=["content1", "content2", "content3"],
            user_id="user1"
        )
        
        assert count == 3
        assert len(mock_manager.saved_items) == 3
    
    def test_clear_not_supported(self):
        """测试清空功能（不支持）"""
        class MockMem0Manager:
            enabled = True
        
        store = VectorStore(mem0_manager=MockMem0Manager())
        result = store.clear("user1")
        
        # 没有 clear 方法，应该返回 False
        assert not result
    
    def test_get_all_not_supported(self):
        """测试获取所有记录（不支持）"""
        class MockMem0Manager:
            enabled = True
        
        store = VectorStore(mem0_manager=MockMem0Manager())
        results = store.get_all("user1")
        
        # 没有 get_all 方法，应该返回空列表
        assert results == []


class TestVectorStoreIntegration:
    """集成测试（需要真实配置）"""
    
    def test_create_from_config_without_mem0(self):
        """测试从配置创建（未启用 Mem0）"""
        config = {
            'enable_mem0': False
        }
        
        store = create_vector_store(config)
        assert not store.enabled
    
    @pytest.mark.skip(reason="需要真实 Mem0 配置")
    def test_create_from_config_with_mem0(self):
        """测试从配置创建（启用 Mem0）"""
        config = {
            'enable_mem0': True,
            'llm_api_key': 'test_key',
            'llm_base_url': 'http://test.com',
            'llm_model': 'test-model'
        }
        
        store = create_vector_store(config)
        # 实际测试需要真实配置
        assert store is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
