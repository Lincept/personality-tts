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
from del_agent.core.llm_adapter import LLMProvider, OpenAICompatibleProvider
from del_agent.utils.config import ConfigManager
from del_agent.backend.factory import DataFactoryPipeline
from del_agent.storage.vector_store import create_vector_store
from del_agent.models.schemas import RawReview
import json
from datetime import datetime
from typing import List, Optional
import os

# 默认不输出 logging（本项目调试输出使用 print + 标志位控制）
logging.getLogger().setLevel(logging.WARNING)


def _truncate(text: str, max_len: int = 180) -> str:
    if text is None:
        return ""
    text = str(text).replace("\n", " ")
    return text if len(text) <= max_len else (text[: max_len - 3] + "...")


class DELAgent:
    """
    DEL Agent 主应用
    
    功能：
    1. 文本模式：使用 FrontendOrchestrator 进行文本交互
    2. 语音模式：使用 VoiceAdapter 进行端到端语音对话
    3. 支持命令行参数切换模式
    """
    
    def __init__(
        self,
        config_path: str = "del_agent/config/settings.yaml",
        trace_frontend: bool = False,
        trace_backend: bool = False
    ):
        """
        初始化 DEL Agent
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.orchestrator = None
        self.llm_provider = None

        self.trace_frontend = trace_frontend
        self.trace_backend = trace_backend
    
    def load_configuration(self) -> None:
        """加载配置（已通过 ConfigManager 自动加载）"""
        print(f"[CONFIG] loaded: {self.config_path}")
    
    def initialize_text_mode(self) -> None:
        """初始化文本模式组件"""
        print("[INIT] text mode...")

        llm_config = self.config_manager.get_llm_config('doubao')
        if not llm_config.api_key:
            raise RuntimeError("未找到豆包 API Key（请设置 ARK_API_KEY 或 DOBAO_API_KEY）")

        self.llm_provider = OpenAICompatibleProvider(
            model_name=llm_config.model_name,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            timeout=llm_config.timeout,
            api_secret=getattr(llm_config, "api_secret", None)
        )

        mem_config = (
            self.config_manager.get_global_config("mem0_config")
            or self.config_manager.get_global_config("memory")
            or {}
        )
        vector_store = create_vector_store(mem_config)

        backend_pipeline = DataFactoryPipeline(
            llm_provider=self.llm_provider,
            enable_verification=False,
            max_retries=3,
            strictness_level=0.7,
            vector_store=vector_store,
            trace_backend=self.trace_backend,
            trace_print=print
        )

        self.orchestrator = FrontendOrchestrator(
            llm_provider=self.llm_provider,
            backend_pipeline=backend_pipeline,
            enable_rag=True,
            rag_retriever=vector_store,
            trace_frontend=self.trace_frontend,
            trace_print=print
        )

        print("[INIT] text mode ready")
    
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

        if not self.orchestrator:
            self.initialize_text_mode()
        
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
                    if self.trace_frontend or self.trace_backend:
                        print("-" * 60)
                        print(f"[TRACE] frontend={self.trace_frontend} backend={self.trace_backend}")
                        print(f"[USER] {_truncate(user_input, 220)}")
                    result = await self.orchestrator.process_user_input(
                        user_id=user_id,
                        user_input=user_input
                    )
                    
                    if result["success"]:
                        print(f"\n助手: {result['response_text']}")
                        
                        # 显示意图类型（调试信息）
                        intent = result.get("intent_type", "unknown")
                        print(f"\n[结果] 意图: {intent}, 耗时: {result['execution_time']:.2f}s")
                    else:
                        print(f"\n[错误] {result.get('error_message', '处理失败')}")
                else:
                    # Orchestrator 未初始化，简单回显
                    print(f"\n助手: [Echo] {user_input}")
                    print("\n[注意] FrontendOrchestrator 未初始化，当前为回显模式")
            
            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except EOFError:
                # stdin 关闭（管道输入结束），优雅退出
                print("\n[EOF] 输入结束，退出")
                break
            except Exception as e:
                print(f"\n[错误] 处理输入时出错: {type(e).__name__}: {e}")
    
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
    
    async def run_data_processing(
        self,
        limit: Optional[int] = None,
        output_dir: Optional[str] = None
    ) -> None:
        """
        运行数据处理模式
        
        处理data/professors目录中的评论数据
        
        Args:
            limit: 限制处理的文件数量，None表示处理全部
            output_dir: 输出目录，保存处理结果
        """
        print("=" * 60)
        print("DEL Agent - 数据处理模式")
        print("=" * 60)
        
        # 获取所有教授数据文件
        professors_dir = Path(__file__).parent / "data" / "professors"
        if not professors_dir.exists():
            print(f"❌ 错误: 找不到目录 {professors_dir}")
            return
        
        json_files = list(professors_dir.glob("*.json"))
        if not json_files:
            print(f"❌ 错误: {professors_dir} 中没有找到JSON文件")
            return
        
        # 限制处理数量
        if limit and limit > 0:
            json_files = json_files[:limit]
            print(f"处理文件数: {len(json_files)} (限制前 {limit} 个)")
        else:
            print(f"处理文件数: {len(json_files)} (全部)")
        
        print("-" * 60)
        
        # 初始化LLM Provider
        try:
            # 从配置管理器获取LLM配置
            llm_config = self.config_manager.get_llm_config('doubao')
            
            # 创建OpenAI兼容的Provider
            llm_provider = OpenAICompatibleProvider(
                model_name=llm_config.model_name,
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                timeout=llm_config.timeout
            )
            print(f"✓ LLM Provider 初始化成功 (model: {llm_config.model_name})")
        except Exception as e:
            print(f"❌ LLM Provider 初始化失败: {e}")
            return
        
        # 初始化数据工厂流水线
        try:
            pipeline = DataFactoryPipeline(
                llm_provider=llm_provider,
                enable_verification=False,  # 可配置
                max_retries=3,
                strictness_level=0.7,
                trace_backend=self.trace_backend,
                trace_print=print
            )
            print("✓ DataFactoryPipeline 初始化成功")
        except Exception as e:
            print(f"❌ DataFactoryPipeline 初始化失败: {e}")
            return
        
        print("-" * 60)
        print()
        
        # 收集所有评论
        all_reviews = []
        file_review_mapping = []  # 记录每个review来自哪个文件
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取评论
                reviews = data.get("data", {}).get("reviews", [])
                professor_info = data.get("input", {})
                
                print(f"📄 {json_file.name}: {len(reviews)} 条评论")
                
                # 转换为RawReview格式
                for review in reviews:
                    description = review.get("description", "").strip()
                    if not description:
                        continue
                    
                    # 解析created_at时间戳
                    created_at_str = review.get("created_at")
                    try:
                        timestamp = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.now()
                    
                    # 构建source_metadata
                    source_metadata = {
                        "professor": professor_info.get("professor", ""),
                        "university": professor_info.get("university", ""),
                        "department": professor_info.get("department", ""),
                        "review_id": review.get("id", ""),
                        "sha1": data.get("sha1", ""),
                        "anonymous": review.get("anonymous", True),
                        "student_relation": review.get("studentProfRelation", 0),
                        "academic": review.get("academic", 0),
                        "job_potential": review.get("jobPotential", 0),
                        "file": json_file.name
                    }
                    
                    raw_review = RawReview(
                        content=description,
                        source_metadata=source_metadata,
                        timestamp=timestamp
                    )
                    
                    all_reviews.append(raw_review)
                    file_review_mapping.append({
                        "file": json_file.name,
                        "professor": professor_info.get("display", "Unknown")
                    })
            
            except Exception as e:
                print(f"❌ 处理文件 {json_file.name} 时出错: {e}")
                continue
        
        print()
        print("=" * 60)
        print(f"共收集到 {len(all_reviews)} 条评论，开始处理...")
        print("=" * 60)
        print()
        
        if not all_reviews:
            print("❌ 没有找到有效的评论数据")
            return
        
        # 批量处理评论
        try:
            results = await pipeline.process_batch(
                all_reviews,
                continue_on_error=True
            )
            
            print()
            print("=" * 60)
            print("处理完成")
            print("=" * 60)
            
            # 显示统计信息
            stats = pipeline.get_statistics()
            print(f"总处理数: {stats['total_processed']}")
            print(f"成功数: {stats['successful']}")
            print(f"失败数: {stats['failed']}")
            print(f"成功率: {stats['success_rate']*100:.1f}%")
            
            # 保存结果
            if output_dir:
                output_path = Path(output_dir)
            else:
                output_path = Path(__file__).parent / "data" / "processed"
            
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 保存处理结果
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"processed_reviews_{timestamp_str}.json"
            
            output_data = {
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "total_files": len(json_files),
                    "total_reviews": len(all_reviews),
                    "statistics": stats
                },
                "results": [
                    {
                        "mentor_id": result.mentor_id,
                        "dimension": result.dimension,
                        "fact_content": result.fact_content,
                        "original_nuance": result.original_nuance,
                        "weight_score": result.weight_score,
                        "tags": result.tags,
                        "last_updated": result.last_updated.isoformat(),
                        "source": file_review_mapping[i] if i < len(file_review_mapping) else {}
                    }
                    for i, result in enumerate(results)
                ]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print()
            print(f"✓ 结果已保存到: {output_file}")
            
        except Exception as e:
            print(f"❌ 批量处理失败: {e}")
            logger.error(f"Batch processing error: {e}", exc_info=True)


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
  
  # 数据处理模式（处理全部数据）
  python main.py --mode process
  
  # 数据处理模式（处理前10个文件）
  python main.py --mode process --limit 10
  
  # 数据处理模式（指定输出目录）
  python main.py --mode process --output ./results
  
  # 启用记忆存储
  python main.py --mode voice --memory
  
  # 启用回声消除
  python main.py --mode voice --aec
        """
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["text", "voice", "process"],
        default="text",
        help="运行模式：text（文本交互）、voice（语音交互）或 process（数据处理）"
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

    parser.add_argument(
        "--trace-frontend",
        action="store_true",
        help="输出前端各模块输入/输出（InfoExtractor/Persona/路由等）"
    )

    parser.add_argument(
        "--trace-backend",
        action="store_true",
        help="输出后端各模块输入/输出（Cleaner/SlangDecoder/Weigher/Compressor 等）"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制处理的文件数量（仅在process模式）"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出目录路径（仅在process模式）"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        # debug 仅用于异常堆栈；常规过程输出仍使用 print + trace 标志位
        logging.getLogger().setLevel(logging.WARNING)
    
    # 创建应用实例
    app = DELAgent(
        config_path=args.config,
        trace_frontend=args.trace_frontend,
        trace_backend=args.trace_backend
    )
    
    try:
        # 加载配置
        app.load_configuration()
        
        # 根据模式运行
        if args.mode == "text":
            # app.initialize_text_mode()
            await app.run_text_mode()
        elif args.mode == "process":
            # 数据处理模式
            await app.run_data_processing(
                limit=args.limit,
                output_dir=args.output
            )
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
