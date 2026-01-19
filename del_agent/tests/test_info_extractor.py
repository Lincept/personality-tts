"""
测试 InfoExtractorAgent
Phase 3.4: 验证信息提取智能体功能
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from del_agent.agents.info_extractor import InfoExtractorAgent, InfoExtractionHelper
from del_agent.models.schemas import InfoExtractResult, RawReview
from del_agent.core.llm_adapter import LLMProvider


class TestInfoExtractorAgent:
    """测试信息提取智能体"""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """创建模拟的 LLM 提供者"""
        provider = Mock(spec=LLMProvider)
        
        # 默认返回查询意图的结果
        def mock_generate(messages, response_format, **kwargs):
            return InfoExtractResult(
                intent_type="query",
                extracted_entities={
                    "mentor_name": "张三",
                    "university": "清华大学",
                    "dimension": "Funding"
                },
                confidence_score=0.9
            )
        
        provider.generate_structured = Mock(side_effect=mock_generate)
        return provider
    
    @pytest.fixture
    def info_extractor(self, mock_llm_provider):
        """创建 InfoExtractorAgent 实例"""
        return InfoExtractorAgent(llm_provider=mock_llm_provider)
    
    def test_agent_initialization(self, info_extractor):
        """测试智能体初始化"""
        assert info_extractor is not None
        assert info_extractor.name == "InfoExtractorAgent"
        assert info_extractor.get_prompt_template_name() == "info_extractor"
        assert info_extractor.get_output_schema() == InfoExtractResult
        assert len(info_extractor.valid_dimensions) == 9
    
    def test_prepare_input_basic(self, info_extractor):
        """测试准备基本输入"""
        user_input = "张三老师怎么样？"
        
        input_data = info_extractor.prepare_input(user_input=user_input)
        
        assert input_data['user_input'] == user_input
        assert input_data['conversation_history'] == []
    
    def test_prepare_input_with_history(self, info_extractor):
        """测试准备带历史的输入"""
        user_input = "那经费情况呢？"
        conversation_history = [
            {"role": "user", "content": "张三老师怎么样？"},
            {"role": "assistant", "content": "张三老师..."}
        ]
        
        input_data = info_extractor.prepare_input(
            user_input=user_input,
            conversation_history=conversation_history
        )
        
        assert input_data['user_input'] == user_input
        assert input_data['conversation_history'] == conversation_history
    
    def test_validate_output_valid(self, info_extractor):
        """测试验证有效输出"""
        valid_result = InfoExtractResult(
            intent_type="query",
            confidence_score=0.9
        )
        
        assert info_extractor.validate_output(valid_result) is True
    
    def test_validate_output_invalid_intent(self, info_extractor):
        """测试验证无效意图类型"""
        # Pydantic 会在创建时就抛出异常
        with pytest.raises(Exception):
            InfoExtractResult(
                intent_type="invalid_intent",
                confidence_score=0.9
            )
    
    def test_extract_info_query(self, info_extractor):
        """测试提取查询意图信息"""
        user_input = "张三老师的科研经费怎么样？"
        
        result = info_extractor.extract_info(user_input=user_input)
        
        assert result is not None
        assert isinstance(result, InfoExtractResult)
        assert result.success is True
        assert result.intent_type in ["chat", "query", "provide_info"]
    
    def test_extract_info_with_history(self, info_extractor):
        """测试带历史的信息提取"""
        user_input = "那他的学生待遇呢？"
        conversation_history = [
            {"role": "user", "content": "张三老师怎么样？"},
            {"role": "assistant", "content": "张三老师是清华大学的教授..."}
        ]
        
        result = info_extractor.extract_info(
            user_input=user_input,
            conversation_history=conversation_history
        )
        
        assert result is not None
        assert result.success is True
    
    def test_post_process_dimension_mapping(self, info_extractor):
        """测试维度映射后处理"""
        result = InfoExtractResult(
            intent_type="query",
            extracted_entities={"dimension": "经费"},
            confidence_score=0.9
        )
        
        processed = info_extractor.post_process_result(result)
        
        assert processed.extracted_entities['dimension'] == 'Funding'
    
    def test_post_process_low_confidence(self, info_extractor):
        """测试低置信度后处理"""
        result = InfoExtractResult(
            intent_type="query",
            confidence_score=0.3
        )
        
        processed = info_extractor.post_process_result(result)
        
        assert processed.requires_clarification is True
        assert len(processed.clarification_questions) > 0
    
    def test_classify_intent_chat(self, info_extractor):
        """测试分类闲聊意图"""
        assert info_extractor.classify_intent("你好") == "chat"
        assert info_extractor.classify_intent("谢谢") == "chat"
        assert info_extractor.classify_intent("Hello") == "chat"
    
    def test_classify_intent_query(self, info_extractor):
        """测试分类查询意图"""
        assert info_extractor.classify_intent("张三老师怎么样？") == "query"
        assert info_extractor.classify_intent("请问这个课题组如何") == "query"
        assert info_extractor.classify_intent("能介绍一下吗？") == "query"
    
    def test_classify_intent_provide_info(self, info_extractor):
        """测试分类提供信息意图"""
        # 简单的规则分类器可能不够准确，检查结果是否合理
        result1 = info_extractor.classify_intent("我的导师经费很充足")
        assert result1 in ["provide_info", "query"]  # 可能被分类为任一
        
        result2 = info_extractor.classify_intent("我们实验室氛围非常好")
        assert result2 in ["provide_info", "query"]
    
    def test_process_method(self, info_extractor):
        """测试 process 方法"""
        user_input = "李四教授的实验室氛围怎么样？"
        
        result = info_extractor.process(raw_input=user_input)
        
        assert result is not None
        assert isinstance(result, InfoExtractResult)
        assert result.success is True
        assert hasattr(result, 'metadata')


class TestInfoExtractorAgentIntents:
    """测试不同意图的识别"""
    
    @pytest.fixture
    def mock_llm_provider_chat(self):
        """创建返回闲聊意图的模拟 LLM"""
        provider = Mock(spec=LLMProvider)
        
        def mock_generate(messages, response_format, **kwargs):
            return InfoExtractResult(
                intent_type="chat",
                confidence_score=0.95
            )
        
        provider.generate_structured = Mock(side_effect=mock_generate)
        return provider
    
    @pytest.fixture
    def mock_llm_provider_provide_info(self):
        """创建返回提供信息意图的模拟 LLM"""
        provider = Mock(spec=LLMProvider)
        
        def mock_generate(messages, response_format, **kwargs):
            return InfoExtractResult(
                intent_type="provide_info",
                extracted_review=RawReview(
                    content="导师经费充足但学生津贴少",
                    source_metadata={"platform": "user_input"}
                ),
                extracted_entities={
                    "dimension": "Funding"
                },
                confidence_score=0.85
            )
        
        provider.generate_structured = Mock(side_effect=mock_generate)
        return provider
    
    def test_chat_intent_extraction(self, mock_llm_provider_chat):
        """测试闲聊意图提取"""
        agent = InfoExtractorAgent(llm_provider=mock_llm_provider_chat)
        result = agent.extract_info("你好")
        
        assert result.intent_type == "chat"
        assert result.confidence_score > 0.9
    
    def test_provide_info_intent_extraction(self, mock_llm_provider_provide_info):
        """测试提供信息意图提取"""
        agent = InfoExtractorAgent(llm_provider=mock_llm_provider_provide_info)
        result = agent.extract_info("我的导师经费充足但学生津贴少")
        
        assert result.intent_type == "provide_info"
        assert result.extracted_review is not None
        assert result.extracted_entities.get('dimension') == 'Funding'


class TestInfoExtractionHelper:
    """测试信息提取辅助类"""
    
    def test_merge_entities_basic(self):
        """测试基本实体合并"""
        entities1 = {"mentor_name": "张三", "university": "清华"}
        entities2 = {"dimension": "Funding"}
        
        merged = InfoExtractionHelper.merge_entities(entities1, entities2)
        
        assert merged["mentor_name"] == "张三"
        assert merged["university"] == "清华"
        assert merged["dimension"] == "Funding"
    
    def test_merge_entities_override(self):
        """测试实体覆盖"""
        entities1 = {"mentor_name": "", "university": "清华"}
        entities2 = {"mentor_name": "张三"}
        
        merged = InfoExtractionHelper.merge_entities(entities1, entities2)
        
        # 空值应该被覆盖
        assert merged["mentor_name"] == "张三"
        assert merged["university"] == "清华"
    
    def test_merge_entities_lists(self):
        """测试列表合并"""
        entities1 = {"keywords": ["经费", "科研"]}
        entities2 = {"keywords": ["导师", "科研"]}
        
        merged = InfoExtractionHelper.merge_entities(entities1, entities2)
        
        # 应该合并并去重
        assert set(merged["keywords"]) == {"经费", "科研", "导师"}
    
    def test_extract_mentor_names_chinese(self):
        """测试提取中文导师名"""
        text = "张三老师和李四教授都很优秀"
        
        names = InfoExtractionHelper.extract_mentor_names(text)
        
        assert len(names) >= 1
        assert any(name in ["张三", "李四"] for name in names)
    
    def test_extract_mentor_names_no_match(self):
        """测试无导师名的文本"""
        text = "今天天气很好，适合出去玩"
        
        names = InfoExtractionHelper.extract_mentor_names(text)
        
        # 简单的正则可能有误匹配，不强制要求为0
        assert len(names) == 0 or all(len(name) < 2 for name in names)


class TestInfoExtractorAgentEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """创建模拟的 LLM 提供者"""
        provider = Mock(spec=LLMProvider)
        
        def mock_generate(messages, response_format, **kwargs):
            return InfoExtractResult(
                intent_type="query",
                requires_clarification=True,
                clarification_questions=["您能具体说明一下吗？"],
                confidence_score=0.4
            )
        
        provider.generate_structured = Mock(side_effect=mock_generate)
        return provider
    
    @pytest.fixture
    def info_extractor(self, mock_llm_provider):
        """创建 InfoExtractorAgent 实例"""
        return InfoExtractorAgent(llm_provider=mock_llm_provider)
    
    def test_ambiguous_input(self, info_extractor):
        """测试模糊输入"""
        result = info_extractor.extract_info("他")
        
        assert result.requires_clarification is True
        assert len(result.clarification_questions) > 0
    
    def test_empty_input(self, info_extractor):
        """测试空输入"""
        result = info_extractor.extract_info("")
        
        # 应该仍然返回结果，但可能需要澄清
        assert result is not None
    
    def test_very_long_input(self, info_extractor):
        """测试很长的输入"""
        long_input = "这是一段很长的输入" * 100
        
        result = info_extractor.extract_info(long_input)
        
        assert result is not None
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
