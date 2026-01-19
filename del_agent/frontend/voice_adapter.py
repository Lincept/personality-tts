"""
Voice Adapter - 语音端到端适配器
集成 doubao_sample 的端到端语音对话能力

版本：1.0.0
创建：Phase 4.1
"""

import asyncio
import sys
import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 延迟导入 doubao_sample，避免在不使用时必须安装 pyaudio
DialogSession = None
doubao_config = None
DOUBAO_SAMPLE_AVAILABLE = False

def _import_doubao_sample():
    """延迟导入 doubao_sample 模块"""
    global DialogSession, doubao_config, DOUBAO_SAMPLE_AVAILABLE
    
    if DialogSession is not None:
        return True
    
    # 添加 doubao_sample 到路径
    doubao_sample_path = Path(__file__).parent.parent.parent / "doubao_sample"
    if not doubao_sample_path.exists():
        logger.error(f"doubao_sample directory not found at: {doubao_sample_path}")
        return False
    
    sys.path.insert(0, str(doubao_sample_path))
    
    try:
        from audio_manager import DialogSession as DS
        import config as dc
        DialogSession = DS
        doubao_config = dc
        DOUBAO_SAMPLE_AVAILABLE = True
        return True
    except ImportError as e:
        logger.error(f"Failed to import doubao_sample: {e}")
        return False


class VoiceAdapter:
    """
    语音适配器
    
    功能：
    1. 封装 doubao_sample 的端到端语音对话能力
    2. 提供简单的接口给主程序使用
    3. 支持音频文件输入和麦克风输入
    4. 支持文本模式和语音模式切换
    
    使用场景：
    - 语音对话模式
    - 音频文件测试
    - 文本交互模式
    
    技术实现：
    - 复用 doubao_sample 的 DialogSession
    - WebSocket 实时通信
    - 端到端语音处理（服务端 ASR + LLM + TTS）
    """
    
    def __init__(
        self,
        mode: str = "audio",
        audio_file_path: str = "",
        output_format: str = "pcm",
        recv_timeout: int = 10,
        enable_memory: bool = False,
        enable_aec: bool = False,
        ws_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化语音适配器
        
        Args:
            mode: 交互模式 ("audio" | "text" | "audio_file")
            audio_file_path: 音频文件路径（仅在 audio_file 模式）
            output_format: 输出音频格式 ("pcm" | "pcm_s16le")
            recv_timeout: 接收超时时间（秒），范围 [10, 120]
            enable_memory: 是否启用记忆存储（VikingDB）
            enable_aec: 是否启用回声消除
            ws_config: WebSocket 配置（可选，默认使用 doubao_config）
        """
        self.mode = mode
        self.audio_file_path = audio_file_path
        self.output_format = output_format
        self.recv_timeout = recv_timeout
        self.enable_memory = enable_memory
        self.enable_aec = enable_aec
        
        # 保存自定义配置，或在 start 时使用 doubao_config
        self._custom_ws_config = ws_config
        
        # DialogSession 将在 start() 中创建
        self.session: Optional[DialogSession] = None
        
        logger.info(f"VoiceAdapter initialized: mode={mode}, format={output_format}")
    
    async def start(self) -> None:
        """
        启动语音对话会话
        
        这会创建 DialogSession 并开始 WebSocket 连接
        """
        # 导入 doubao_sample
        if not _import_doubao_sample():
            raise ImportError(
                "无法导入 doubao_sample 模块。\n"
                "请确保:\n"
                "1. doubao_sample 目录存在\n"
                "2. 已安装所需依赖: pip install pyaudio websockets\n"
                "3. 参考 doubao_sample/requirements.txt"
            )
        
        try:
            logger.info("Starting voice dialog session...")
            
            # 使用自定义配置或 doubao_config
            ws_config = self._custom_ws_config or doubao_config.ws_connect_config
            
            # 创建对话会话
            self.session = DialogSession(
                ws_config=ws_config,
                output_audio_format=self.output_format,
                audio_file_path=self.audio_file_path,
                mod=self.mode,
                recv_timeout=self.recv_timeout,
                use_memory=self.enable_memory,
                use_aec=self.enable_aec
            )
            
            # 启动会话（这会阻塞直到会话结束）
            await self.session.start()
            
            logger.info("Voice dialog session completed")
            
        except Exception as e:
            logger.error(f"Error in voice dialog session: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """
        停止语音对话会话
        """
        if self.session:
            try:
                # DialogSession 会在用户中断时自动清理
                logger.info("Voice dialog session stopped")
            except Exception as e:
                logger.error(f"Error stopping session: {e}")
    
    @staticmethod
    def check_environment() -> Dict[str, bool]:
        """
        检查环境配置
        
        Returns:
            配置状态字典
        """
        doubao_sample_path = Path(__file__).parent.parent.parent / "doubao_sample"
        
        status = {
            "doubao_app_id": bool(os.getenv("DOUBAO_APP_ID")),
            "doubao_access_key": bool(os.getenv("DOUBAO_ACCESS_KEY")),
            "vikingdb_configured": bool(
                os.getenv("VIKINGDB_AK") and os.getenv("VIKINGDB_SK")
            ),
            "doubao_sample_available": doubao_sample_path.exists()
        }
        
        return status
    
    @staticmethod
    def validate_config() -> tuple[bool, list[str]]:
        """
        验证配置是否完整
        
        Returns:
            (is_valid, missing_items)
        """
        doubao_sample_path = Path(__file__).parent.parent.parent / "doubao_sample"
        missing = []
        
        if not os.getenv("DOUBAO_APP_ID"):
            missing.append("DOUBAO_APP_ID")
        if not os.getenv("DOUBAO_ACCESS_KEY"):
            missing.append("DOUBAO_ACCESS_KEY")
        if not doubao_sample_path.exists():
            missing.append(f"doubao_sample directory at {doubao_sample_path}")
        
        is_valid = len(missing) == 0
        return is_valid, missing


class VoiceAdapterFactory:
    """
    语音适配器工厂
    提供便捷的创建方法
    """
    
    @staticmethod
    def create_microphone_adapter(
        enable_memory: bool = False,
        enable_aec: bool = False
    ) -> VoiceAdapter:
        """
        创建麦克风输入的语音适配器
        
        Args:
            enable_memory: 是否启用记忆存储
            enable_aec: 是否启用回声消除
        """
        return VoiceAdapter(
            mode="audio",
            enable_memory=enable_memory,
            enable_aec=enable_aec
        )
    
    @staticmethod
    def create_file_adapter(
        audio_file_path: str,
        enable_memory: bool = False
    ) -> VoiceAdapter:
        """
        创建音频文件输入的语音适配器
        
        Args:
            audio_file_path: 音频文件路径
            enable_memory: 是否启用记忆存储
        """
        return VoiceAdapter(
            mode="audio",  # 会自动检测为 audio_file
            audio_file_path=audio_file_path,
            enable_memory=enable_memory
        )
    
    @staticmethod
    def create_text_adapter(
        recv_timeout: int = 120,
        enable_memory: bool = False
    ) -> VoiceAdapter:
        """
        创建文本交互的语音适配器
        
        Args:
            recv_timeout: 接收超时（文本模式可以更长）
            enable_memory: 是否启用记忆存储
        """
        return VoiceAdapter(
            mode="text",
            recv_timeout=recv_timeout,
            enable_memory=enable_memory
        )


# 便捷函数
async def start_voice_conversation(
    mode: str = "audio",
    audio_file: Optional[str] = None,
    enable_memory: bool = False,
    enable_aec: bool = False
) -> None:
    """
    启动语音对话（便捷函数）
    
    Args:
        mode: 交互模式 ("audio" | "text")
        audio_file: 音频文件路径（可选）
        enable_memory: 是否启用记忆存储
        enable_aec: 是否启用回声消除
    """
    # 验证配置
    is_valid, missing = VoiceAdapter.validate_config()
    if not is_valid:
        logger.error(f"Configuration incomplete. Missing: {', '.join(missing)}")
        print(f"❌ 配置不完整，缺少: {', '.join(missing)}")
        print("\n请设置以下环境变量:")
        print("  export DOUBAO_APP_ID=your_app_id")
        print("  export DOUBAO_ACCESS_KEY=your_access_key")
        return
    
    # 创建适配器
    if audio_file:
        adapter = VoiceAdapterFactory.create_file_adapter(audio_file, enable_memory)
    elif mode == "text":
        adapter = VoiceAdapterFactory.create_text_adapter(enable_memory=enable_memory)
    else:
        adapter = VoiceAdapterFactory.create_microphone_adapter(enable_memory, enable_aec)
    
    # 启动会话
    try:
        await adapter.start()
    except KeyboardInterrupt:
        logger.info("User interrupted")
        await adapter.stop()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
