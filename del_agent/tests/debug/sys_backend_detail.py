#!/usr/bin/env python3
"""
系统调试 - 后端数据工厂详细流程
详细展示后端数据工厂各个Agent的处理过程，包括：
- RawCommentCleaner（清洗）
- SlangDecoderAgent（黑话解码）
- WeigherAgent（权重分析）
- CompressorAgent（结构化压缩）
- CriticAgent（可选核验）

版本：3.0.0 - 简化日志输出
更新：2026-01-20
"""

import sys
import asyncio
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入流程可视化器（从同一目录）
from flow_visualizer import create_backend_flow, create_frontend_flow, create_full_interaction_flow

from del_agent.backend.factory import DataFactoryPipeline
from del_agent.frontend.orchestrator import FrontendOrchestrator
from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.models.schemas import RawReview, StructuredKnowledgeNode


class DetailedDebugLogger:
    """详细调试日志管理器 - 使用简洁的print输出"""
    
    def __init__(self, log_dir: Path):
        # 设置历史日志目录
        self.log_dir = log_dir / "history"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成带时间戳的日志文件名（保存在history目录）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = self.log_dir / f"debug_backend_{timestamp}.log"
        
        # 最新日志文件（保存在debug/logs目录）
        self.latest_log_file_path = log_dir / "latest_run.log"
        
        # 打开文件句柄
        self.history_file = open(self.log_file_path, 'w', encoding='utf-8')
        self.latest_file = open(self.latest_log_file_path, 'w', encoding='utf-8')
        
        self.step_count = 0
        self.performance_data = {}
    
    def __del__(self):
        """析构函数，关闭文件句柄"""
        if hasattr(self, 'history_file'):
            self.history_file.close()
        if hasattr(self, 'latest_file'):
            self.latest_file.close()
    
    def write(self, message: str, console: bool = True):
        """统一的输出方法：写入两个文件和控制台"""
        # 写入历史日志
        self.history_file.write(message + '\n')
        self.history_file.flush()
        
        # 写入最新日志
        self.latest_file.write(message + '\n')
        self.latest_file.flush()
        
        # 输出到控制台
        if console:
            print(message)
    
    def print_header(self, title: str):
        """打印大标题"""
        line = "=" * 80
        self.write("")
        self.write(line)
        self.write(title.center(80))
        self.write(line)
        self.write("")
    
    def print_section(self, title: str):
        """打印小标题"""
        line = "-" * 80
        self.write("")
        self.write(line)
        self.write(f"📌 {title}")
        self.write(line)
        self.write("")
    
    def log_step_start(self, step_name: str, description: str = ""):
        """记录步骤开始"""
        self.step_count += 1
        self.write(f"▶ Step {self.step_count}: {step_name}")
        if description:
            self.write(f"   {description}")
        self.write("")
        return time.time()
    
    def log_step_end(self, step_name: str, start_time: float, success: bool = True):
        """记录步骤结束"""
        elapsed = time.time() - start_time
        self.performance_data[step_name] = elapsed
        
        status = "✓" if success else "✗"
        self.write(f"{status} {step_name} 完成 (耗时: {elapsed:.3f}s)")
        self.write("")
    
    def log_data(self, label: str, data: Any):
        """记录数据"""
        if isinstance(data, dict):
            formatted = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        elif hasattr(data, 'model_dump'):
            formatted = json.dumps(data.model_dump(), ensure_ascii=False, indent=2, default=str)
        else:
            formatted = str(data)
        
        self.write(f"{label}:")
        self.write(formatted)
        self.write("")
    
    def print_frontend_flow(self, user_input: str, extract_result: Dict[str, Any], user_profile: Dict[str, Any] = None):
        """打印前端处理流程图 - 展示前端各Agent的数据流动"""
        self.print_section("前端处理流程图")
        
        # 使用封装的可视化器生成流程图
        flow_lines = create_frontend_flow(
            user_input=user_input,
            extract_result=extract_result,
            user_profile=user_profile,
            box_width=72
        )
        
        for line in flow_lines:
            self.write(line)
    
    def print_data_flow(self, agent_outputs: Dict[str, Any], raw_content: str):
        """打印后端数据流程图 - 展示关键数据在各模块间的流动"""
        self.print_section("后端数据流程图")
        
        self.write("")
        # 使用新的可视化器生成流程图
        flow_lines = create_backend_flow(
            raw_content=raw_content,
            agent_outputs=agent_outputs,
            box_width=72
        )
        
        for line in flow_lines:
            self.write(line)
        self.write("")
    
    def print_performance_summary(self):
        """打印性能摘要"""
        self.print_section("性能统计摘要")
        
        total_time = sum(self.performance_data.values())
        self.write(f"总耗时: {total_time:.3f}s")
        self.write("")
        
        self.write("各步骤耗时:")
        for step, elapsed in sorted(self.performance_data.items(), key=lambda x: x[1], reverse=True):
            percentage = (elapsed / total_time * 100) if total_time > 0 else 0
            self.write(f"  {step}: {elapsed:.3f}s ({percentage:.1f}%)")
        
        self.write("")
        self.write(f"历史日志已保存到: {self.log_file_path}")
        self.write(f"最新日志已保存到: {self.latest_log_file_path}")


class BackendDebugRunner:
    """后端调试运行器 - 拦截并详细记录数据工厂的处理过程"""
    
    def __init__(self, logger: DetailedDebugLogger):
        self.logger = logger
        self.pipeline = None
        self.orchestrator = None
    
    def setup(self):
        """初始化系统"""
        start_time = self.logger.log_step_start(
            "系统初始化",
            "加载环境变量，创建LLM Provider，初始化数据工厂"
        )
        
        # 加载环境变量
        env_path = PROJECT_ROOT / "del_agent" / ".env"
        load_dotenv(dotenv_path=env_path)
        
        api_key = os.getenv("ARK_API_KEY")
        if not api_key:
            self.logger.write("❌ 未找到 ARK_API_KEY 环境变量")
            return False
        
        # 创建LLM Provider
        llm = OpenAICompatibleProvider(
            model_name="doubao-seed-1-6-251015",
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        
        self.logger.log_data("LLM Provider配置", {
            "base_url": llm.base_url,
            "model_name": llm.model_name,
            "api_key": api_key[:10] + "..."
        })
        
        # 创建数据工厂
        self.pipeline = DataFactoryPipeline(llm_provider=llm)
        
        # 创建前端编排器
        self.orchestrator = FrontendOrchestrator(
            llm_provider=llm,
            backend_pipeline=self.pipeline
        )
        
        self.logger.log_data("前端编排器配置", {
            "组件": "FrontendOrchestrator",
            "后端集成": "DataFactoryPipeline",
            "支持模式": ["chat", "query", "provide_info"]
        })
        
        self.logger.log_step_end("系统初始化", start_time, True)
        return True
    
    async def process_review(self, raw_review: RawReview, enable_verification: bool = True):
        """处理单条评价 - 详细展示每个Agent的处理过程"""
        source_id = raw_review.source_metadata.get('source_id', 'unknown')
        self.logger.print_section(f"处理评价: {source_id}")
        
        self.logger.log_data("原始评价数据", raw_review)
        
        start_time = self.logger.log_step_start(
            "数据工厂处理",
            f"启用核验: {enable_verification}"
        )
        
        try:
            # 记录每个Agent的输出
            agent_outputs = {}
            
            self.logger.write("")
            self.logger.write("─" * 70)
            self.logger.write("  开始数据工厂流水线处理...")
            self.logger.write("─" * 70)

            # ========== Step 1: RawCommentCleaner (清洗) ==========
            step_start = time.time()
            self.logger.write("")
            self.logger.write("  🔹 Agent: RawCommentCleaner (清洗)")
            
            cleaning_result = await self.pipeline.cleaner.process(raw_review.content)
            agent_outputs['cleaner'] = cleaning_result
            
            step_elapsed = time.time() - step_start
            self.logger.write(f"     输出: factual_content={cleaning_result.factual_content[:60]}...")
            self.logger.write(f"     情绪强度: {cleaning_result.emotional_intensity}")
            self.logger.write(f"     关键词数: {len(cleaning_result.keywords)}")
            self.logger.write(f"     耗时: {step_elapsed:.3f}s")
            
            # ========== Step 2: SlangDecoderAgent (黑话解码) ==========
            step_start = time.time()
            self.logger.write("")
            self.logger.write("  🔹 Agent: SlangDecoderAgent (黑话解码)")
            
            decoding_result = await self.pipeline.decoder.process(cleaning_result.factual_content)
            agent_outputs['decoder'] = decoding_result
            
            step_elapsed = time.time() - step_start
            self.logger.write(f"     输出: decoded_text={decoding_result.decoded_text[:60]}...")
            self.logger.write(f"     识别黑话数: {len(decoding_result.slang_dictionary)}")
            self.logger.write(f"     耗时: {step_elapsed:.3f}s")
            
            # ========== Step 3: WeigherAgent (权重分析) ==========
            step_start = time.time()
            self.logger.write("")
            self.logger.write("  🔹 Agent: WeigherAgent (权重分析)")
            weigher_input = {
                'content': cleaning_result.factual_content,
                'source_metadata': raw_review.source_metadata,
                'timestamp': raw_review.timestamp,
                'emotional_intensity': cleaning_result.emotional_intensity
            }
            
            weight_result = self.pipeline.weigher.process(weigher_input)
            agent_outputs['weigher'] = weight_result
            
            step_elapsed = time.time() - step_start
            self.logger.write(f"     最终权重: {weight_result.weight_score:.3f}")
            self.logger.write(f"     身份可信度: {weight_result.identity_confidence:.3f}")
            self.logger.write(f"     时间衰减: {weight_result.time_decay:.3f}")
            self.logger.write(f"     离群点状态: {weight_result.outlier_status}")
            self.logger.write(f"     耗时: {step_elapsed:.3f}s")
            
            # ========== Step 4: CompressorAgent (结构化压缩) ==========
            step_start = time.time()
            self.logger.write("")
            self.logger.write("  🔹 Agent: CompressorAgent (结构化压缩)")
            compressor_input = {
                'factual_content': cleaning_result.factual_content,
                'weight_score': weight_result.weight_score,
                'keywords': cleaning_result.keywords,
                'original_text': raw_review.content
            }
            
            compression_result = self.pipeline.compressor.process(compressor_input)
            agent_outputs['compressor'] = compression_result
            
            step_elapsed = time.time() - step_start
            self.logger.write(f"     维度: {compression_result.structured_node.dimension}")
            self.logger.write(f"     导师ID: {compression_result.structured_node.mentor_id}")
            self.logger.write(f"     事实内容: {compression_result.structured_node.fact_content[:60]}...")
            self.logger.write(f"     标签数: {len(compression_result.structured_node.tags)}")
            self.logger.write(f"     耗时: {step_elapsed:.3f}s")
            
            self.logger.write("")
            self.logger.write("─" * 70)
            self.logger.write("  数据工厂流水线处理完成")
            self.logger.write("─" * 70)
            
            self.logger.log_step_end("数据工厂处理", start_time, True)
            
            # ========== 数据流程图 ==========
            self.logger.print_data_flow(agent_outputs, raw_review.content)
            
            # ========== 输出各Agent详细结果 ==========
            self.logger.print_section("各Agent详细输出")
            
            self.logger.write("📋 1. RawCommentCleaner (清洗) 输出:")
            self.logger.log_data("", agent_outputs['cleaner'])
            
            self.logger.write("📋 2. SlangDecoderAgent (黑话解码) 输出:")
            self.logger.log_data("", agent_outputs['decoder'])
            
            self.logger.write("📋 3. WeigherAgent (权重分析) 输出:")
            self.logger.log_data("", agent_outputs['weigher'])
            
            self.logger.write("📋 4. CompressorAgent (结构化压缩) 输出:")
            self.logger.log_data("", agent_outputs['compressor'])
            
            # ========== 输出最终结果 ==========
            self.logger.print_section("最终结果")
            result = compression_result.structured_node
            self.logger.log_data("结构化知识节点", result)
            
            return result
            
        except Exception as e:
            self.logger.log_step_end("数据工厂处理", start_time, False)
            self.logger.write(f"❌ 处理失败: {str(e)}")
            import traceback
            self.logger.write(traceback.format_exc())
            return None
    
    async def process_batch(self, reviews: List[RawReview], enable_verification: bool = True):
        """批量处理评价"""
        self.logger.print_header("批量处理评价")
        
        results = []
        for i, review in enumerate(reviews, 1):
            self.logger.write("")
            self.logger.write("=" * 80)
            self.logger.write(f"处理第 {i}/{len(reviews)} 条评价")
            self.logger.write("=" * 80)
            
            result = await self.process_review(review, enable_verification)
            if result:
                results.append(result)
        
        return results
    
    async def process_full_interaction(self, user_id: str, user_input: str, input_type: str = "provide_info"):
        """
        处理完整的前后端交互流程
        
        Args:
            user_id: 用户ID
            user_input: 用户输入（评价文本）
            input_type: 输入类型（chat/query/provide_info）
        """
        self.logger.print_header(f"完整交互流程测试: {input_type}")
        
        overall_start = time.time()
        
        # ========== 阶段1: 用户输入 ==========
        self.logger.print_section("阶段 1: 用户输入")
        self.logger.write(f"👤 用户ID: {user_id}")
        self.logger.write(f"💬 用户输入: {user_input}")
        self.logger.write(f"🎯 预期意图: {input_type}")
        self.logger.write("")
        
        # ========== 阶段2: 前端接收和意图识别 ==========
        step_start = self.logger.log_step_start(
            "前端处理",
            "Orchestrator接收输入，意图识别，路由分发"
        )
        
        try:
            # 调用前端编排器处理
            frontend_result = await self.orchestrator.process_user_input(
                user_id=user_id,
                user_input=user_input,
                additional_context={"test_mode": True}
            )
            
            self.logger.log_step_end("前端处理", step_start, True)
            
            # ========== 阶段2.1: 前端Agent详细输出 ==========
            self.logger.print_section("前端Agent处理详情")
            
            # InfoExtractorAgent输出
            extract_result = frontend_result.get('extract_result', {})
            self.logger.write("")
            self.logger.write("📋 1. InfoExtractorAgent (意图识别) 输出:")
            self.logger.log_data("", extract_result)
            
            # 获取用户画像
            user_profile = self.orchestrator.profile_manager.get_profile(user_id)
            self.logger.write("")
            self.logger.write("📋 2. UserProfileManager (用户画像):")
            self.logger.log_data("", {
                "user_id": user_id,
                "personality_vector": user_profile.model_dump() if user_profile else None,
                "interaction_count": getattr(user_profile, 'interaction_count', 0) if user_profile else 0
            })
            
            # 前端数据流程图
            self.logger.print_frontend_flow(
                user_input=user_input,
                extract_result=extract_result,
                user_profile={
                    "personality_vector": user_profile.model_dump() if user_profile else {},
                    "interaction_count": getattr(user_profile, 'interaction_count', 0) if user_profile else 0
                }
            )
            
            # 显示前端处理结果
            self.logger.write("")
            self.logger.write("📊 前端处理结果:")
            self.logger.write(f"   检测意图: {frontend_result.get('intent', 'unknown')}")
            self.logger.write(f"   响应文本: {frontend_result.get('response_text', '')[:100]}...")
            self.logger.write(f"   执行时间: {frontend_result.get('execution_time', 0):.3f}s")
            
            # 如果有后端处理记录，显示后端数据流
            if 'backend_processing' in frontend_result.get('metadata', {}):
                backend_info = frontend_result['metadata']['backend_processing']
                self.logger.write("")
                self.logger.write("🔄 后端处理信息:")
                self.logger.write(f"   是否调用后端: {backend_info.get('called', False)}")
                if backend_info.get('called'):
                    self.logger.write(f"   后端耗时: {backend_info.get('execution_time', 0):.3f}s")
                    self.logger.write(f"   处理状态: {backend_info.get('status', 'unknown')}")
            
            # ========== PersonaAgent响应生成 ==========
            self.logger.write("")
            self.logger.write("📋 3. PersonaAgent (个性化响应生成):")
            response_text = frontend_result.get('response_text', '')
            persona_strategy = frontend_result.get('metadata', {}).get('persona_strategy', 'default')
            self.logger.log_data("", {
                "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                "strategy": persona_strategy,
                "response_length": len(response_text)
            })
            
            # ========== 完整流程图 ==========
            self.logger.print_section("完整交互流程图")
            self._print_full_interaction_flow(user_input, frontend_result)
            
            # ========== 输出详细结果 ==========
            self.logger.print_section("详细结果")
            self.logger.log_data("前端完整响应", frontend_result)
            
            # 统计总耗时
            total_time = time.time() - overall_start
            self.logger.write("")
            self.logger.write(f"✅ 完整交互流程总耗时: {total_time:.3f}s")
            
            return frontend_result
            
        except Exception as e:
            self.logger.log_step_end("前端处理", step_start, False)
            self.logger.write(f"❌ 前端处理失败: {str(e)}")
            import traceback
            self.logger.write(traceback.format_exc())
            return None
    
    def _print_full_interaction_flow(self, user_input: str, result: Dict[str, Any]):
        """打印完整的前后端交互流程图"""
        def truncate(text, max_len=50):
            return text[:max_len] + "..." if len(text) > max_len else text
        
        intent = result.get('intent', 'unknown')
        response = result.get('response_text', '')
        metadata = result.get('metadata', {})
        
        self.logger.write("")
        self.logger.write("╔════════════════════════════════════════════════════════════════════════╗")
        self.logger.write("║  🌐 完整交互流程：用户 → 前端 → 后端 → 前端 → 用户                    ║")
        self.logger.write("╚════════════════════════════════════════════════════════════════════════╝")
        self.logger.write("")
        
        # 用户输入
        self.logger.write("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        self.logger.write("┃  👤 用户输入                                                           ┃")
        self.logger.write(f"┃  💬 {truncate(user_input, 60).ljust(60)} ┃")
        self.logger.write("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        self.logger.write("                                 ↓")
        
        # 前端接收
        self.logger.write("┌────────────────────────────────────────────────────────────────────────┐")
        self.logger.write("│ 🎯 前端：Orchestrator (编排器)                                         │")
        self.logger.write("├────────────────────────────────────────────────────────────────────────┤")
        self.logger.write(f"│   ① 意图识别: {intent.ljust(57)} │")
        self.logger.write(f"│   ② 路由决策: {'调用后端' if metadata.get('backend_processing', {}).get('called') else '直接响应'.ljust(55)} │")
        self.logger.write("└────────────────────────────────────────────────────────────────────────┘")
        self.logger.write("                                 ↓")
        
        # 如果有后端处理
        if metadata.get('backend_processing', {}).get('called'):
            backend_info = metadata['backend_processing']
            
        # 使用封装的可视化器生成流程图
        flow_lines = create_full_interaction_flow(
            user_input=user_input,
            result=result,
            box_width=72
        )
        
        for line in flow_lines:
            self.logger.write(line)


# =============================================================================
# 主测试函数
# =============================================================================

async def main():
    """运行后端数据工厂详细调试测试"""
    
    # 设置日志目录
    debug_dir = PROJECT_ROOT / "del_agent" / "tests" / "debug" / "logs"
    logger = DetailedDebugLogger(debug_dir)
    
    logger.print_header("后端数据工厂详细调试测试")
    
    # ====================================
    # 初始化
    # ====================================
    runner = BackendDebugRunner(logger)
    
    if not runner.setup():
        logger.write("❌ 系统初始化失败")
        return
    
    # ====================================
    # 测试用例 1: 单条评价处理（含黑话）
    # ====================================
    logger.print_header("测试用例 1: 单条评价处理（含黑话）")
    
    review1 = RawReview(
        content="导师真是学术妲己，总是画饼却从不兑现。实验室设备老旧，经费紧张，压力山大。",
        source_metadata={
            "source_id": "test_001",
            "reviewer_type": "student",
            "platform": "test"
        },
        timestamp=datetime.now()
    )
    
    result1 = await runner.process_review(review1, enable_verification=True)
    
    # ====================================
    # 测试用例 2: 单条评价处理（不含黑话）
    # ====================================
    logger.print_header("测试用例 2: 单条评价处理（不含黑话）")
    
    review2 = RawReview(
        content="导师经常出差，很少有时间指导学生。实验室氛围比较冷清，大家各做各的。发表论文压力很大。",
        source_metadata={
            "source_id": "test_002",
            "reviewer_type": "student",
            "platform": "test"
        },
        timestamp=datetime.now()
    )
    
    result2 = await runner.process_review(review2, enable_verification=False)
    
    # ====================================
    # 测试用例 3: 前后端完整交互（提供信息）
    # ====================================
    logger.print_header("测试用例 3: 前后端完整交互 - 提供导师评价信息")
    
    interaction_result1 = await runner.process_full_interaction(
        user_id="test_user_001",
        user_input="我想分享一下对张老师的评价。他是个很负责的导师，虽然要求严格，但对学生的成长很用心，经常指导我们发论文。",
        input_type="provide_info"
    )
    
    # ====================================
    # 测试用例 4: 前后端完整交互（查询信息）
    # ====================================
    logger.print_header("测试用例 4: 前后端完整交互 - 查询导师信息")
    
    interaction_result2 = await runner.process_full_interaction(
        user_id="test_user_002",
        user_input="请问张老师怎么样？他的实验室环境如何？",
        input_type="query"
    )
    
    # ====================================
    # 总结
    # ====================================
    logger.print_header("测试完成")
    
    logger.write(f"后端测试: 2条评价处理")
    logger.write(f"  - 成功处理: {(1 if result1 else 0) + (1 if result2 else 0)}")
    logger.write("")
    logger.write(f"前后端交互测试: 2个完整流程")
    logger.write(f"  - 提供信息流程: {'✓' if interaction_result1 else '✗'}")
    logger.write(f"  - 查询信息流程: {'✓' if interaction_result2 else '✗'}")
    
    logger.print_performance_summary()
    
    logger.write("")
    logger.write("=" * 80)
    logger.write("调试会话结束".center(80))
    logger.write("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
