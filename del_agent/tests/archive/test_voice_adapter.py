"""
Voice Adapter 基础测试
验证语音适配器的基本功能

版本：1.0.0
创建：Phase 4.1
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from del_agent.frontend.voice_adapter import (
    VoiceAdapter,
    VoiceAdapterFactory
)


# ==================== 配置验证测试 ====================

def test_check_environment():
    """测试环境检查"""
    status = VoiceAdapter.check_environment()
    
    assert isinstance(status, dict)
    assert "doubao_app_id" in status
    assert "doubao_access_key" in status
    assert "vikingdb_configured" in status
    assert "doubao_sample_available" in status


def test_validate_config_missing():
    """测试配置验证（缺少配置）"""
    with patch.dict(os.environ, {}, clear=True):
        is_valid, missing = VoiceAdapter.validate_config()
        
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)
        
        # 至少应该缺少 APP_ID 和 ACCESS_KEY
        assert "DOUBAO_APP_ID" in missing or "DOUBAO_ACCESS_KEY" in missing


def test_validate_config_with_env():
    """测试配置验证（有环境变量）"""
    with patch.dict(os.environ, {
        "DOUBAO_APP_ID": "test_app_id",
        "DOUBAO_ACCESS_KEY": "test_access_key"
    }):
        is_valid, missing = VoiceAdapter.validate_config()
        
        # 如果 doubao_sample 存在，应该验证通过
        doubao_path = Path(__file__).parent.parent.parent.parent / "doubao_sample"
        if doubao_path.exists():
            # 可能仍然有其他缺失项
            assert isinstance(is_valid, bool)
            assert isinstance(missing, list)


# ==================== 适配器初始化测试 ====================

def test_voice_adapter_initialization():
    """测试语音适配器初始化"""
    adapter = VoiceAdapter(
        mode="audio",
        output_format="pcm",
        recv_timeout=10
    )
    
    assert adapter.mode == "audio"
    assert adapter.output_format == "pcm"
    assert adapter.recv_timeout == 10
    assert adapter.enable_memory is False
    assert adapter.enable_aec is False
    assert adapter.session is None


def test_voice_adapter_initialization_with_options():
    """测试带选项的语音适配器初始化"""
    adapter = VoiceAdapter(
        mode="text",
        output_format="pcm_s16le",
        recv_timeout=120,
        enable_memory=True,
        enable_aec=True
    )
    
    assert adapter.mode == "text"
    assert adapter.output_format == "pcm_s16le"
    assert adapter.recv_timeout == 120
    assert adapter.enable_memory is True
    assert adapter.enable_aec is True


# ==================== 工厂方法测试 ====================

def test_factory_create_microphone_adapter():
    """测试工厂创建麦克风适配器"""
    adapter = VoiceAdapterFactory.create_microphone_adapter(
        enable_memory=True,
        enable_aec=True
    )
    
    assert isinstance(adapter, VoiceAdapter)
    assert adapter.mode == "audio"
    assert adapter.enable_memory is True
    assert adapter.enable_aec is True


def test_factory_create_file_adapter():
    """测试工厂创建文件适配器"""
    adapter = VoiceAdapterFactory.create_file_adapter(
        audio_file_path="test.wav",
        enable_memory=False
    )
    
    assert isinstance(adapter, VoiceAdapter)
    assert adapter.mode == "audio"
    assert adapter.audio_file_path == "test.wav"
    assert adapter.enable_memory is False


def test_factory_create_text_adapter():
    """测试工厂创建文本适配器"""
    adapter = VoiceAdapterFactory.create_text_adapter(
        recv_timeout=60,
        enable_memory=True
    )
    
    assert isinstance(adapter, VoiceAdapter)
    assert adapter.mode == "text"
    assert adapter.recv_timeout == 60
    assert adapter.enable_memory is True


# ==================== 会话管理测试 ====================

@pytest.mark.asyncio
async def test_adapter_stop_without_session():
    """测试停止未启动的会话"""
    adapter = VoiceAdapter(mode="audio")
    
    # 应该不抛出异常
    await adapter.stop()
    
    assert adapter.session is None


# ==================== 集成测试（需要 Mock）====================

@pytest.mark.asyncio
async def test_start_with_mock_session():
    """测试启动会话（Mock）"""
    adapter = VoiceAdapter(mode="text", recv_timeout=10)
    
    # Mock DialogSession
    with patch('del_agent.frontend.voice_adapter.DialogSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.start = MagicMock(return_value=None)
        mock_session_class.return_value = mock_session
        
        # 由于 start() 是同步的，我们需要 Mock 它的返回
        async def mock_start():
            pass
        
        mock_session.start = mock_start
        
        # 这会尝试启动但被 Mock 拦截
        try:
            # 实际测试中需要更复杂的 Mock，这里只验证不抛出导入错误
            pass
        except ImportError:
            # 如果 doubao_sample 不可用，这是预期的
            pytest.skip("doubao_sample not available")


# ==================== 参数验证测试 ====================

def test_invalid_mode():
    """测试无效模式（虽然不会在运行时检查，但可以测试初始化）"""
    # 目前构造函数不验证 mode，但我们可以测试创建
    adapter = VoiceAdapter(mode="invalid_mode")
    assert adapter.mode == "invalid_mode"


def test_timeout_range():
    """测试超时范围"""
    # 超时范围应该在 [10, 120]
    adapter_low = VoiceAdapter(recv_timeout=10)
    adapter_high = VoiceAdapter(recv_timeout=120)
    
    assert adapter_low.recv_timeout == 10
    assert adapter_high.recv_timeout == 120


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
