#!/usr/bin/env python3
"""
DEL Agent - 统一入口
支持文本交互和语音交互双模式

版本：1.0.0
创建：Phase 4.2
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from del_agent.frontend.orchestrator import FrontendOrchestrator
from del_agent.frontend.voice_adapter import VoiceAdapter, start_voice_conversation
from del_agent.core.llm_adapter import LLMProvider
from del_agent.utils.config import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DELAgent:
    """
    DEL Agent 主应用
    
    功能：
    1. 文本模式：使用 FrontendOrchestrator 进行文本交互
    2. 语音模式：使用 VoiceAdapter 进行端到端语音对话
    3. 支持命令行参数切换模式
    """
    
    def __init__(self, config_path: str = "del_agent/config/settings.yaml"):
        """
        初始化 DEL Agent
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.orchestrator = None
        self.llm_provider = None
    
    def load_configuration(self) -> None:
        """加载配置（已通过 ConfigManager 自动加载）"""
        logger.info(f"Configuration loaded from {self.config_path}")
    
    def initialize_text_mode(self) -> None:
        """初始化文本模式组件"""
        logger.info("Initializing text mode components...")
        
        # 创建 LLM Provider
        # 这里需要根据实际配置创建，暂时使用占位
        # self.llm_provider = LLMProvider(...)
        
        # 创建 Orchestrator
        # self.orchestrator = FrontendOrchestrator(
        #     llm_provider=self.llm_provider,
        #     enable_rag=False
        # )
        
        logger.info("Text mode initialized")
    
    async def run_text_mode(self) -> None:
        """
        运行文本交互模式
        
        使用 FrontendOrchestrator 处理用户输入
        """
        print("=" * 60)
        print("DEL Agent - 文本交互模式")
        print("=" * 60)
        print("提示：输入 'quit' 或 'exit' 退出")
        print("提示：输入 'clear' 清空对话历史")
        print("-" * 60)
        
        user_id = "default_user"
        
        while True:
            try:
                # 读取用户输入
                user_input = input("\n用户: ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n再见！")
                    break
                
                if user_input.lower() == 'clear':
                    if self.orchestrator:
                        self.orchestrator.clear_conversation(user_id)
                    print("✓ 对话历史已清空")
                    continue
                
                # 处理用户输入
                if self.orchestrator:
                    result = await self.orchestrator.process_user_input(
                        user_id=user_id,
                        user_input=user_input
                    )
                    
                    if result["success"]:
                        print(f"\n助手: {result['response_text']}")
                        
                        # 显示意图类型（调试信息）
                        intent = result.get("intent_type", "unknown")
                        print(f"\n[调试] 意图: {intent}, 执行时间: {result['execution_time']:.2f}s")
                    else:
                        print(f"\n[错误] {result.get('error_message', '处理失败')}")
                else:
                    # Orchestrator 未初始化，简单回显
                    print(f"\n助手: [Echo] {user_input}")
                    print("\n[注意] FrontendOrchestrator 未初始化，当前为回显模式")
            
            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except Exception as e:
                logger.error(f"Error processing input: {e}", exc_info=True)
                print(f"\n[错误] 处理输入时出错: {e}")
    
    async def run_voice_mode(
        self,
        audio_file: str = "",
        enable_memory: bool = False,
        enable_aec: bool = False
    ) -> None:
        """
        运行语音交互模式
        
        使用 VoiceAdapter 进行端到端语音对话
        
        Args:
            audio_file: 音频文件路径（可选）
            enable_memory: 是否启用记忆存储
            enable_aec: 是否启用回声消除
        """
        print("=" * 60)
        print("DEL Agent - 语音交互模式")
        print("=" * 60)
        
        if audio_file:
            print(f"音频文件: {audio_file}")
        else:
            print("输入源: 麦克风")
        
        print(f"记忆存储: {'启用' if enable_memory else '禁用'}")
        print(f"回声消除: {'启用' if enable_aec else '禁用'}")
        print("-" * 60)
        print("按 Ctrl+C 结束对话")
        print("=" * 60)
        print()
        
        # 启动语音对话
        mode = "audio"
        await start_voice_conversation(
            mode=mode,
            audio_file=audio_file if audio_file else None,
            enable_memory=enable_memory,
            enable_aec=enable_aec
        )


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="DEL Agent - 导师评价与信息提取智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 文本交互模式
  python main.py --mode text
  
  # 语音交互模式（麦克风）
  python main.py --mode voice
  
  # 语音交互模式（音频文件）
  python main.py --mode voice --audio data/test.wav
  
  # 启用记忆存储
  python main.py --mode voice --memory
  
  # 启用回声消除
  python main.py --mode voice --aec
        """
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["text", "voice"],
        default="text",
        help="交互模式：text（文本）或 voice（语音）"
    )
    
    parser.add_argument(
        "--audio",
        type=str,
        default="",
        help="音频文件路径（仅在语音模式）"
    )
    
    parser.add_argument(
        "--memory",
        action="store_true",
        help="启用记忆存储（VikingDB）"
    )
    
    parser.add_argument(
        "--aec",
        action="store_true",
        help="启用回声消除（AEC）"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="del_agent/config/settings.yaml",
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建应用实例
    app = DELAgent(config_path=args.config)
    
    try:
        # 加载配置
        app.load_configuration()
        
        # 根据模式运行
        if args.mode == "text":
            # app.initialize_text_mode()
            await app.run_text_mode()
        else:  # voice
            # 检查环境配置
            is_valid, missing = VoiceAdapter.validate_config()
            if not is_valid:
                print(f"❌ 语音模式配置不完整，缺少: {', '.join(missing)}")
                print("\n请设置以下环境变量:")
                print("  export DOUBAO_APP_ID=your_app_id")
                print("  export DOUBAO_ACCESS_KEY=your_access_key")
                print("\n或创建 doubao_sample/.env 文件（参考 .env.example）")
                sys.exit(1)
            
            await app.run_voice_mode(
                audio_file=args.audio,
                enable_memory=args.memory,
                enable_aec=args.aec
            )
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
