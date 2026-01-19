"""
测试 PersonaAgent
Phase 3.3: 验证个性化对话智能体功能
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from del_agent.agents.persona import PersonaAgent
from del_agent.models.schemas import PersonaResponse, UserPersonalityVector
from del_agent.core.llm_adapter import LLMProvider


class TestPersonaAgent:
    """测试个性化对话智能体"""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """创建模拟的 LLM 提供者"""
        provider = Mock(spec=LLMProvider)
        
        # 模拟 generate_structured 方法
        def mock_generate(messages, response_format, **kwargs):
            return PersonaResponse(
                response_text="这是一个根据用户画像生成的个性化回复。",
                applied_style={
                    "humor_level": 0.7,
                    "formality_level": 0.4,
                    "detail_level": 0.6
                },
                confidence_score=0.9,
                requires_followup=False,
                suggested_topics=["导师", "科研"]
            )
        
        provider.generate_structured = Mock(side_effect=mock_generate)
        return provider
    
    @pytest.fixture
    def persona_agent(self, mock_llm_provider):
        """创建 PersonaAgent 实例"""
        return PersonaAgent(llm_provider=mock_llm_provider)
    
    @pytest.fixture
    def user_profile(self):
        """创建测试用户画像"""
        return UserPersonalityVector(
            user_id="test_user",
            humor_preference=0.7,
            formality_level=0.4,
            detail_preference=0.6,
            language_style="casual",
            preferred_topics=["导师", "科研"],
            interaction_history_count=5
        )
    
    def test_agent_initialization(self, persona_agent):
        """测试智能体初始化"""
        assert persona_agent is not None
        assert persona_agent.name == "PersonaAgent"
        assert persona_agent.get_prompt_template_name() == "persona"
        assert persona_agent.get_output_schema() == PersonaResponse
    
    def test_prepare_input_with_profile(self, persona_agent, user_profile):
        """测试准备输入数据（带用户画像）"""
        query = "导师的科研情况如何？"
        conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好！有什么可以帮您的吗？"}
        ]
        rag_context = "张三老师是清华大学的教授，主要研究方向是人工智能。"
        
        input_data = persona_agent.prepare_input(
            query=query,
            user_profile=user_profile,
            conversation_history=conversation_history,
            rag_context=rag_context
        )
        
        assert input_data['query'] == query
        assert input_data['humor_level'] == 0.7
        assert input_data['formality_level'] == 0.4
        assert input_data['detail_level'] == 0.6
        assert input_data['language_style'] == "casual"
        assert input_data['preferred_topics'] == ["导师", "科研"]
        assert input_data['interaction_count'] == 5
        assert input_data['conversation_history'] == conversation_history
        assert input_data['rag_context'] == rag_context
    
    def test_prepare_input_without_profile(self, persona_agent):
        """测试准备输入数据（无用户画像，使用默认）"""
        query = "你好"
        
        input_data = persona_agent.prepare_input(query=query)
        
        assert input_data['query'] == query
        assert input_data['humor_level'] == 0.5  # 默认值
        assert input_data['formality_level'] == 0.5
        assert input_data['detail_level'] == 0.5
        assert input_data['conversation_history'] == []
        assert input_data['rag_context'] == ""
    
    def test_validate_output_valid(self, persona_agent):
        """测试验证有效的输出"""
        valid_output = PersonaResponse(
            response_text="这是一个合适长度的回复，内容充实且准确。",
            confidence_score=0.9
        )
        
        assert persona_agent.validate_output(valid_output) is True
    
    def test_validate_output_empty(self, persona_agent):
        """测试验证空回复"""
        empty_output = PersonaResponse(
            response_text="",
            confidence_score=0.9
        )
        
        assert persona_agent.validate_output(empty_output) is False
    
    def test_validate_output_too_short(self, persona_agent):
        """测试验证过短的回复"""
        short_output = PersonaResponse(
            response_text="好的",
            confidence_score=0.9
        )
        
        assert persona_agent.validate_output(short_output) is False
    
    def test_validate_output_too_long(self, persona_agent):
        """测试验证过长的回复"""
        long_output = PersonaResponse(
            response_text="x" * 6000,  # 超过 5000 字符
            confidence_score=0.9
        )
        
        assert persona_agent.validate_output(long_output) is False
    
    def test_generate_response_basic(self, persona_agent, user_profile):
        """测试基本的回复生成"""
        query = "导师的科研水平怎么样？"
        
        response = persona_agent.generate_response(
            query=query,
            user_profile=user_profile
        )
        
        assert response is not None
        assert isinstance(response, PersonaResponse)
        assert response.success is True
        assert len(response.response_text) > 0
        assert response.confidence_score > 0
    
    def test_generate_response_with_history(self, persona_agent, user_profile):
        """测试带对话历史的回复生成"""
        query = "那经费情况呢？"
        conversation_history = [
            {"role": "user", "content": "导师的科研水平怎么样？"},
            {"role": "assistant", "content": "导师的科研水平很高..."}
        ]
        
        response = persona_agent.generate_response(
            query=query,
            user_profile=user_profile,
            conversation_history=conversation_history
        )
        
        assert response is not None
        assert response.success is True
    
    def test_generate_response_with_rag(self, persona_agent, user_profile):
        """测试带 RAG 上下文的回复生成"""
        query = "这位老师适合报考吗？"
        rag_context = "张三老师发表了100+篇论文，经费充足，实验室氛围好。"
        
        response = persona_agent.generate_response(
            query=query,
            user_profile=user_profile,
            rag_context=rag_context
        )
        
        assert response is not None
        assert response.success is True
    
    def test_adjust_style_by_feedback_formal(self, persona_agent, user_profile):
        """测试根据反馈调整风格（太正式）"""
        feedback = "回复太正式了，能不能随意一点？"
        
        adjustments = persona_agent.adjust_style_by_feedback(
            user_profile=user_profile,
            feedback=feedback
        )
        
        assert 'formality_level' in adjustments
        assert adjustments['formality_level'] < user_profile.formality_level
    
    def test_adjust_style_by_feedback_serious(self, persona_agent, user_profile):
        """测试根据反馈调整风格（太严肃）"""
        feedback = "太严肃了，希望轻松一点"
        
        adjustments = persona_agent.adjust_style_by_feedback(
            user_profile=user_profile,
            feedback=feedback
        )
        
        assert 'humor_preference' in adjustments
        assert adjustments['humor_preference'] > user_profile.humor_preference
    
    def test_adjust_style_by_feedback_brief(self, persona_agent, user_profile):
        """测试根据反馈调整风格（太简单）"""
        feedback = "回复太简单了，我想要更详细的信息"
        
        adjustments = persona_agent.adjust_style_by_feedback(
            user_profile=user_profile,
            feedback=feedback
        )
        
        assert 'detail_preference' in adjustments
        assert adjustments['detail_preference'] > user_profile.detail_preference
    
    def test_process_method(self, persona_agent, user_profile):
        """测试 process 方法"""
        query = "请介绍一下这位导师"
        
        result = persona_agent.process(
            raw_input=query,
            user_profile=user_profile
        )
        
        assert result is not None
        assert isinstance(result, PersonaResponse)
        assert result.success is True
        assert hasattr(result, 'metadata')


class TestPersonaAgentStyleModulation:
    """测试风格调节功能"""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """创建模拟的 LLM 提供者"""
        provider = Mock(spec=LLMProvider)
        
        def mock_generate(messages, response_format, **kwargs):
            return PersonaResponse(
                response_text="风格调节后的回复",
                applied_style={"humor_level": 0.8},
                confidence_score=0.85
            )
        
        provider.generate_structured = Mock(side_effect=mock_generate)
        return provider
    
    @pytest.fixture
    def persona_agent(self, mock_llm_provider):
        """创建 PersonaAgent 实例"""
        return PersonaAgent(llm_provider=mock_llm_provider)
    
    def test_high_humor_profile(self, persona_agent):
        """测试高幽默用户画像"""
        profile = UserPersonalityVector(
            user_id="funny_user",
            humor_preference=0.9,
            formality_level=0.2,
            detail_preference=0.4
        )
        
        input_data = persona_agent.prepare_input(
            query="test",
            user_profile=profile
        )
        
        assert input_data['humor_level'] == 0.9
        assert input_data['formality_level'] == 0.2
    
    def test_formal_profile(self, persona_agent):
        """测试正式用户画像"""
        profile = UserPersonalityVector(
            user_id="formal_user",
            humor_preference=0.2,
            formality_level=0.9,
            detail_preference=0.8
        )
        
        input_data = persona_agent.prepare_input(
            query="test",
            user_profile=profile
        )
        
        assert input_data['formality_level'] == 0.9
        assert input_data['humor_level'] == 0.2
        assert input_data['detail_level'] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
