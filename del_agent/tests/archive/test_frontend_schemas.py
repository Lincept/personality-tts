"""
测试前端交互层数据模型
Phase 3.1: 验证 UserPersonalityVector 和 InfoExtractResult
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from del_agent.models.schemas import (
    UserPersonalityVector,
    InfoExtractResult,
    RawReview
)


class TestUserPersonalityVector:
    """测试用户画像向量模型"""
    
    def test_create_default_profile(self):
        """测试创建默认用户画像"""
        profile = UserPersonalityVector(user_id="test_user_001")
        
        assert profile.user_id == "test_user_001"
        assert profile.humor_preference == 0.5
        assert profile.formality_level == 0.5
        assert profile.detail_preference == 0.5
        assert profile.interaction_history_count == 0
        assert profile.preferred_topics == []
        assert profile.language_style == "neutral"
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.updated_at, datetime)
    
    def test_create_custom_profile(self):
        """测试创建自定义用户画像"""
        profile = UserPersonalityVector(
            user_id="test_user_002",
            humor_preference=0.8,
            formality_level=0.3,
            detail_preference=0.7,
            interaction_history_count=15,
            preferred_topics=["科研", "导师", "经费"],
            language_style="casual"
        )
        
        assert profile.user_id == "test_user_002"
        assert profile.humor_preference == 0.8
        assert profile.formality_level == 0.3
        assert profile.detail_preference == 0.7
        assert profile.interaction_history_count == 15
        assert profile.preferred_topics == ["科研", "导师", "经费"]
        assert profile.language_style == "casual"
    
    def test_invalid_preference_range(self):
        """测试无效的偏好值范围"""
        with pytest.raises(ValidationError):
            UserPersonalityVector(
                user_id="test_user_003",
                humor_preference=1.5  # 超出范围
            )
        
        with pytest.raises(ValidationError):
            UserPersonalityVector(
                user_id="test_user_004",
                formality_level=-0.1  # 低于范围
            )
    
    def test_invalid_language_style(self):
        """测试无效的语言风格"""
        with pytest.raises(ValidationError):
            UserPersonalityVector(
                user_id="test_user_005",
                language_style="invalid_style"
            )
    
    def test_update_profile(self):
        """测试更新用户画像"""
        profile = UserPersonalityVector(user_id="test_user_006")
        
        # 模拟更新
        original_created = profile.created_at
        profile.humor_preference = 0.9
        profile.interaction_history_count += 1
        profile.updated_at = datetime.now()
        
        assert profile.humor_preference == 0.9
        assert profile.interaction_history_count == 1
        assert profile.created_at == original_created
        assert profile.updated_at > original_created


class TestInfoExtractResult:
    """测试信息提取结果模型"""
    
    def test_create_chat_intent(self):
        """测试创建闲聊意图"""
        result = InfoExtractResult(
            intent_type="chat",
            confidence_score=0.95
        )
        
        assert result.intent_type == "chat"
        assert result.extracted_review is None
        assert result.confidence_score == 0.95
        assert result.requires_clarification is False
        assert result.clarification_questions == []
        assert result.success is True
    
    def test_create_query_intent(self):
        """测试创建查询意图"""
        result = InfoExtractResult(
            intent_type="query",
            extracted_entities={
                "mentor_name": "张三",
                "university": "清华大学"
            },
            confidence_score=0.85
        )
        
        assert result.intent_type == "query"
        assert result.extracted_entities["mentor_name"] == "张三"
        assert result.extracted_entities["university"] == "清华大学"
        assert result.confidence_score == 0.85
    
    def test_create_provide_info_intent(self):
        """测试创建提供信息意图"""
        raw_review = RawReview(
            content="导师经费很充足，但学生津贴较少",
            source_metadata={"platform": "test"}
        )
        
        result = InfoExtractResult(
            intent_type="provide_info",
            extracted_review=raw_review,
            extracted_entities={
                "dimension": "Funding"
            },
            confidence_score=0.9
        )
        
        assert result.intent_type == "provide_info"
        assert result.extracted_review is not None
        assert result.extracted_review.content == "导师经费很充足，但学生津贴较少"
        assert result.extracted_entities["dimension"] == "Funding"
    
    def test_requires_clarification(self):
        """测试需要澄清的情况"""
        result = InfoExtractResult(
            intent_type="query",
            requires_clarification=True,
            clarification_questions=[
                "您指的是哪个大学的张三老师？",
                "您想了解哪个方面的信息？"
            ],
            confidence_score=0.6
        )
        
        assert result.requires_clarification is True
        assert len(result.clarification_questions) == 2
        assert result.confidence_score == 0.6
    
    def test_invalid_intent_type(self):
        """测试无效的意图类型"""
        with pytest.raises(ValidationError):
            InfoExtractResult(
                intent_type="invalid_intent"
            )
    
    def test_invalid_confidence_score(self):
        """测试无效的置信度"""
        with pytest.raises(ValidationError):
            InfoExtractResult(
                intent_type="chat",
                confidence_score=1.5  # 超出范围
            )
        
        with pytest.raises(ValidationError):
            InfoExtractResult(
                intent_type="chat",
                confidence_score=-0.1  # 低于范围
            )
    
    def test_with_metadata(self):
        """测试带元数据的提取结果"""
        result = InfoExtractResult(
            intent_type="query",
            metadata={
                "user_id": "user_123",
                "session_id": "session_456",
                "context": "follow_up_question"
            }
        )
        
        assert result.metadata["user_id"] == "user_123"
        assert result.metadata["session_id"] == "session_456"
        assert result.metadata["context"] == "follow_up_question"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
