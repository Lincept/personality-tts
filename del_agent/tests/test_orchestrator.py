"""
FrontendOrchestrator 测试套件
测试前端编排器的路由和集成功能

版本：1.0.0
创建：Phase 3.5
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from del_agent.models.schemas import (
    InfoExtractResult,
    PersonaResponse,
    UserPersonalityVector,
    RawReview,
    CompressionResult
)
from del_agent.frontend.orchestrator import FrontendOrchestrator, ConversationContext
from del_agent.core.llm_adapter import LLMProvider


# ==================== Fixtures ====================

@pytest.fixture
def mock_llm_provider():
    """Mock LLM Provider"""
    provider = Mock(spec=LLMProvider)
    provider.generate = AsyncMock(return_value="Mock LLM response")
    provider.generate_json = AsyncMock(return_value={"result": "mock"})
    return provider


@pytest.fixture
def orchestrator(mock_llm_provider):
    """创建测试用的 Orchestrator"""
    return FrontendOrchestrator(
        llm_provider=mock_llm_provider,
        enable_rag=False,
        max_conversation_history=5
    )


# ==================== ConversationContext 测试 ====================

def test_conversation_context_creation():
    """测试对话上下文创建"""
    context = ConversationContext(user_id="test_user", max_history=5)
    
    assert context.user_id == "test_user"
    assert context.max_history == 5
    assert len(context.history) == 0
    assert isinstance(context.created_at, datetime)


def test_conversation_context_add_turn():
    """测试添加对话轮次"""
    context = ConversationContext(user_id="test_user", max_history=5)
    
    context.add_turn("Hello", "Hi there!")
    
    assert len(context.history) == 2
    assert context.history[0]["role"] == "user"
    assert context.history[0]["content"] == "Hello"
    assert context.history[1]["role"] == "assistant"
    assert context.history[1]["content"] == "Hi there!"


def test_conversation_context_max_history():
    """测试对话历史上限"""
    context = ConversationContext(user_id="test_user", max_history=2)
    
    # 添加3轮对话（超过上限）
    context.add_turn("Q1", "A1")
    context.add_turn("Q2", "A2")
    context.add_turn("Q3", "A3")
    
    # 应该只保留最近2轮（4条消息）
    assert len(context.history) == 4
    assert context.history[0]["content"] == "Q2"


def test_conversation_context_get_history_text():
    """测试获取历史文本"""
    context = ConversationContext(user_id="test_user")
    
    context.add_turn("Hello", "Hi!")
    context.add_turn("How are you?", "I'm fine!")
    
    history_text = context.get_history_text()
    
    assert "用户: Hello" in history_text
    assert "助手: Hi!" in history_text
    assert "用户: How are you?" in history_text
    assert "助手: I'm fine!" in history_text


def test_conversation_context_clear():
    """测试清空历史"""
    context = ConversationContext(user_id="test_user")
    
    context.add_turn("Hello", "Hi!")
    assert len(context.history) == 2
    
    context.clear()
    assert len(context.history) == 0


# ==================== FrontendOrchestrator 基础测试 ====================

def test_orchestrator_initialization(orchestrator):
    """测试编排器初始化"""
    assert orchestrator.llm_provider is not None
    assert orchestrator.info_extractor is not None
    assert orchestrator.persona_agent is not None
    assert orchestrator.profile_manager is not None
    assert len(orchestrator.conversations) == 0


def test_orchestrator_get_or_create_context(orchestrator):
    """测试获取或创建对话上下文"""
    user_id = "test_user_123"
    
    # 第一次获取，应该创建新的
    context1 = orchestrator.get_or_create_context(user_id)
    assert context1.user_id == user_id
    assert len(orchestrator.conversations) == 1
    
    # 第二次获取，应该返回同一个
    context2 = orchestrator.get_or_create_context(user_id)
    assert context1 is context2


def test_orchestrator_clear_conversation(orchestrator):
    """测试清空对话"""
    user_id = "test_user_456"
    
    context = orchestrator.get_or_create_context(user_id)
    context.add_turn("Hello", "Hi!")
    
    assert len(context.history) == 2
    
    orchestrator.clear_conversation(user_id)
    assert len(context.history) == 0


def test_orchestrator_get_conversation_stats(orchestrator):
    """测试获取对话统计"""
    user_id = "test_user_789"
    
    context = orchestrator.get_or_create_context(user_id)
    context.add_turn("Q1", "A1")
    context.add_turn("Q2", "A2")
    
    stats = orchestrator.get_conversation_stats(user_id)
    
    assert stats["user_id"] == user_id
    assert stats["conversation_turns"] == 2
    assert "created_at" in stats
    assert "profile" in stats


# ==================== 路由功能测试 ====================

@pytest.mark.asyncio
async def test_orchestrator_process_chat_intent(orchestrator, mock_llm_provider):
    """测试闲聊意图处理"""
    user_id = "test_user_chat"
    user_input = "你好，今天天气真好！"
    
    # Mock InfoExtractor 返回闲聊意图
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(return_value=InfoExtractResult(
            intent_type="chat",
            confidence_score=0.9
        ))
    ):
        # Mock PersonaAgent 返回回复
        with patch.object(
            orchestrator.persona_agent,
            'process',
            new=AsyncMock(return_value=PersonaResponse(
                response_text="你好！是啊，今天天气不错呢！",
                applied_style={"humor_level": 0.5}
            ))
        ):
            result = await orchestrator.process_user_input(user_id, user_input)
            
            assert result["success"] is True
            assert result["intent_type"] == "chat"
            assert "你好" in result["response_text"]
            assert result["additional_info"]["mode"] == "chat"


@pytest.mark.asyncio
async def test_orchestrator_process_query_intent(orchestrator, mock_llm_provider):
    """测试查询意图处理"""
    user_id = "test_user_query"
    user_input = "张三老师的科研经费情况怎么样？"
    
    # Mock InfoExtractor 返回查询意图
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(return_value=InfoExtractResult(
            intent_type="query",
            confidence_score=0.9,
            extracted_entities={
                "mentor_name": "张三",
                "dimension": "Funding"
            }
        ))
    ):
        # Mock PersonaAgent 返回回复
        with patch.object(
            orchestrator.persona_agent,
            'process',
            new=AsyncMock(return_value=PersonaResponse(
                response_text="根据记录，张三老师的经费情况...",
                applied_style={"formality_level": 0.6}
            ))
        ):
            result = await orchestrator.process_user_input(user_id, user_input)
            
            assert result["success"] is True
            assert result["intent_type"] == "query"
            assert "经费" in result["response_text"] or "张三" in result["response_text"]
            assert result["additional_info"]["mode"] == "query"
            assert "extracted_entities" in result["additional_info"]


@pytest.mark.asyncio
async def test_orchestrator_process_provide_info_intent(orchestrator, mock_llm_provider):
    """测试提供信息意图处理（有完整RawReview）"""
    user_id = "test_user_info"
    user_input = "我想评价一下张三老师，他经费很充足，但学生津贴少"
    
    # 创建完整的 RawReview
    mock_review = RawReview(
        content="经费很充足，但学生津贴少",
        source_metadata={"source": "user_input", "mentor_id": "mentor_zhang_san", "dimension": "Funding"}
    )
    
    # Mock InfoExtractor 返回提供信息意图
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(return_value=InfoExtractResult(
            intent_type="provide_info",
            confidence_score=0.9,
            extracted_review=mock_review,
            extracted_entities={
                "mentor_name": "张三",
                "dimension": "Funding"
            }
        ))
    ):
        # Mock PersonaAgent 返回确认回复
        with patch.object(
            orchestrator.persona_agent,
            'process',
            new=AsyncMock(return_value=PersonaResponse(
                response_text="感谢您的评价！我们已经记录了您对张三老师的反馈。",
                applied_style={"formality_level": 0.5}
            ))
        ):
            result = await orchestrator.process_user_input(user_id, user_input)
            
            assert result["success"] is True
            assert result["intent_type"] == "provide_info"
            assert result["additional_info"]["mode"] == "info_submission"
            assert result["additional_info"]["status"] == "processed"


@pytest.mark.asyncio
async def test_orchestrator_process_provide_info_needs_clarification(orchestrator, mock_llm_provider):
    """测试提供信息意图处理（需要澄清）"""
    user_id = "test_user_clarify"
    user_input = "我想评价一下某个老师"
    
    # Mock InfoExtractor 返回需要澄清
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(return_value=InfoExtractResult(
            intent_type="provide_info",
            confidence_score=0.6,
            extracted_review=None,  # 没有提取到完整信息
            requires_clarification=True,
            clarification_questions=["请问是哪位老师？", "您想评价哪个方面？"]
        ))
    ):
        result = await orchestrator.process_user_input(user_id, user_input)
        
        assert result["success"] is True
        assert result["intent_type"] == "provide_info"
        assert result["additional_info"]["mode"] == "info_submission"
        assert result["additional_info"]["status"] == "needs_clarification"
        assert "请问是哪位老师？" in result["response_text"]


# ==================== 集成测试 ====================

@pytest.mark.asyncio
async def test_orchestrator_multi_turn_conversation(orchestrator, mock_llm_provider):
    """测试多轮对话"""
    user_id = "test_user_multi"
    
    # 第一轮：闲聊
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(return_value=InfoExtractResult(intent_type="chat", confidence_score=0.9))
    ):
        with patch.object(
            orchestrator.persona_agent,
            'process',
            new=AsyncMock(return_value=PersonaResponse(response_text="你好！", applied_style={}))
        ):
            result1 = await orchestrator.process_user_input(user_id, "你好")
            assert result1["success"] is True
    
    # 第二轮：查询
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(return_value=InfoExtractResult(intent_type="query", confidence_score=0.9))
    ):
        with patch.object(
            orchestrator.persona_agent,
            'process',
            new=AsyncMock(return_value=PersonaResponse(response_text="好的，让我查一下", applied_style={}))
        ):
            result2 = await orchestrator.process_user_input(user_id, "查询一下张三老师")
            assert result2["success"] is True
    
    # 检查对话历史
    context = orchestrator.get_or_create_context(user_id)
    assert len(context.history) == 4  # 2轮对话 = 4条消息


@pytest.mark.asyncio
async def test_orchestrator_error_handling(orchestrator, mock_llm_provider):
    """测试错误处理"""
    user_id = "test_user_error"
    user_input = "测试错误处理"
    
    # Mock InfoExtractor 抛出异常
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(side_effect=Exception("Test error"))
    ):
        result = await orchestrator.process_user_input(user_id, user_input)
        
        assert result["success"] is False
        assert "error_message" in result
        assert "Test error" in result["error_message"]


# ==================== 用户画像集成测试 ====================

@pytest.mark.asyncio
async def test_orchestrator_user_profile_update(orchestrator, mock_llm_provider):
    """测试用户画像更新"""
    user_id = "test_user_profile"
    
    # 初始画像
    initial_profile = orchestrator.profile_manager.get_profile(user_id)
    initial_count = initial_profile.interaction_history_count
    
    # 进行一次交互
    with patch.object(
        orchestrator.info_extractor,
        'process',
        new=AsyncMock(return_value=InfoExtractResult(intent_type="chat", confidence_score=0.9))
    ):
        with patch.object(
            orchestrator.persona_agent,
            'process',
            new=AsyncMock(return_value=PersonaResponse(response_text="回复", applied_style={}))
        ):
            await orchestrator.process_user_input(user_id, "测试输入")
    
    # 检查画像是否更新
    updated_profile = orchestrator.profile_manager.get_profile(user_id)
    assert updated_profile.interaction_history_count == initial_count + 1


# ==================== 运行测试 ====================

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "-s"])
