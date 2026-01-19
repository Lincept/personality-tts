"""
数据工厂流水线控制器 (DataFactoryPipeline)
负责编排所有后端智能体的执行顺序
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.llm_adapter import LLMProvider
from models.schemas import (
    RawReview,
    StructuredKnowledgeNode,
    CommentCleaningResult,
    SlangDecodingResult,
    WeightAnalysisResult,
    CompressionResult
)
from agents.raw_comment_cleaner import RawCommentCleaner
from agents.slang_decoder import SlangDecoderAgent
from agents.weigher import WeigherAgent
from agents.compressor import CompressorAgent
from agents.critic import CriticAgent

logger = logging.getLogger(__name__)


class DataFactoryPipeline:
    """
    后端数据工厂流水线
    
    流程：
    RawReview → CleanerAgent → SlangDecoderAgent → WeigherAgent 
              → CompressorAgent → StructuredKnowledgeNode
              
    每个步骤都可选配 CriticAgent 进行核验
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        enable_verification: bool = False,
        max_retries: int = 3,
        strictness_level: float = 0.7,
        slang_dict_storage: str = "json",
        slang_dict_path: Optional[str] = None
    ):
        """
        初始化数据工厂流水线
        
        Args:
            llm_provider: LLM提供者实例
            enable_verification: 是否启用核验循环
            max_retries: 最大重试次数
            strictness_level: 严格度等级
            slang_dict_storage: 黑话词典存储方式 ("json" or "mem0")
            slang_dict_path: 黑话词典路径
        """
        self.llm_provider = llm_provider
        self.enable_verification = enable_verification
        self.max_retries = max_retries
        self.strictness_level = strictness_level
        
        # 初始化各个智能体
        logger.info("Initializing DataFactoryPipeline...")
        
        self.cleaner = RawCommentCleaner(llm_provider)
        logger.info("✓ RawCommentCleaner initialized")
        
        self.decoder = SlangDecoderAgent(
            llm_provider,
            storage_type=slang_dict_storage,
            storage_path=slang_dict_path
        )
        logger.info("✓ SlangDecoderAgent initialized")
        
        self.weigher = WeigherAgent(llm_provider)
        logger.info("✓ WeigherAgent initialized")
        
        self.compressor = CompressorAgent(llm_provider)
        logger.info("✓ CompressorAgent initialized")
        
        # 初始化判别器（如果启用）
        if enable_verification:
            self.critic = CriticAgent(
                llm_provider,
                strictness_level=strictness_level
            )
            logger.info("✓ CriticAgent initialized")
        else:
            self.critic = None
        
        logger.info(f"DataFactoryPipeline initialized (verification={enable_verification})")
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "verification_passes": 0,
            "verification_failures": 0
        }
    
    def process_raw_review(
        self,
        raw_review: RawReview,
        enable_verification_override: Optional[bool] = None
    ) -> StructuredKnowledgeNode:
        """
        处理原始评价数据
        
        Args:
            raw_review: 原始评价数据
            enable_verification_override: 是否覆盖默认的核验设置
        
        Returns:
            StructuredKnowledgeNode: 结构化知识节点
        
        Raises:
            Exception: 处理失败时抛出异常
        """
        start_time = datetime.now()
        self.stats["total_processed"] += 1
        
        # 初始化步骤耗时记录
        step_timings = {}
        
        try:
            logger.info(f"Processing raw review: {raw_review.content[:50]}...")
            
            # 确定是否启用核验
            use_verification = (
                enable_verification_override 
                if enable_verification_override is not None 
                else self.enable_verification
            )
            
            # Step 1: 清洗评论
            step1_start = datetime.now()
            logger.info("Step 1/4: Cleaning comment...")
            if use_verification and self.critic:
                cleaned = self.cleaner.process_with_verification(
                    raw_review.content,
                    critic_agent=self.critic,
                    max_retries=self.max_retries,
                    strictness_level=self.strictness_level
                )
                self.stats["verification_passes"] += 1
            else:
                cleaned = self.cleaner.process(raw_review.content)
            
            step_timings["step1_cleaning"] = (datetime.now() - step1_start).total_seconds()
            logger.info(
                f"✓ Cleaned in {step_timings['step1_cleaning']:.2f}s: "
                f"{cleaned.factual_content[:50]}..."
            )
            
            # Step 2: 解码黑话
            step2_start = datetime.now()
            logger.info("Step 2/4: Decoding slang...")
            decoded = self.decoder.process(cleaned.factual_content)
            step_timings["step2_decoding"] = (datetime.now() - step2_start).total_seconds()
            logger.info(
                f"✓ Decoded in {step_timings['step2_decoding']:.2f}s: "
                f"{len(decoded.slang_dictionary)} slang terms found"
            )
            
            # Step 3: 计算权重
            step3_start = datetime.now()
            logger.info("Step 3/4: Analyzing weight...")
            weight_input = {
                "content": decoded.decoded_text,
                "source_metadata": raw_review.source_metadata,
                "timestamp": raw_review.timestamp
            }
            weight_result = self.weigher.process(weight_input)
            step_timings["step3_weighing"] = (datetime.now() - step3_start).total_seconds()
            logger.info(
                f"✓ Weight analyzed in {step_timings['step3_weighing']:.2f}s: "
                f"score={weight_result.weight_score:.2f}"
            )
            
            # Step 4: 结构化压缩
            step4_start = datetime.now()
            logger.info("Step 4/4: Compressing to knowledge node...")
            compression_input = {
                "factual_content": decoded.decoded_text,
                "weight_score": weight_result.weight_score,
                "keywords": cleaned.keywords,
                "original_nuance": raw_review.content[:50] + "...",
                "source_metadata": raw_review.source_metadata
            }
            compression_result = self.compressor.process(compression_input)
            step_timings["step4_compression"] = (datetime.now() - step4_start).total_seconds()
            logger.info(
                f"✓ Compressed in {step_timings['step4_compression']:.2f}s: "
                f"dimension={compression_result.structured_node.dimension}"
            )
            
            # 获取最终的知识节点
            knowledge_node = compression_result.structured_node
            
            # 更新统计
            self.stats["successful"] += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 输出详细的性能报告
            logger.info(
                f"✅ Pipeline completed successfully in {execution_time:.2f}s\n"
                f"   ├─ Step 1 (Cleaning):    {step_timings['step1_cleaning']:.2f}s "
                f"({step_timings['step1_cleaning']/execution_time*100:.1f}%)\n"
                f"   ├─ Step 2 (Decoding):    {step_timings['step2_decoding']:.2f}s "
                f"({step_timings['step2_decoding']/execution_time*100:.1f}%)\n"
                f"   ├─ Step 3 (Weighing):    {step_timings['step3_weighing']:.2f}s "
                f"({step_timings['step3_weighing']/execution_time*100:.1f}%)\n"
                f"   └─ Step 4 (Compression): {step_timings['step4_compression']:.2f}s "
                f"({step_timings['step4_compression']/execution_time*100:.1f}%)\n"
                f"   Result: Mentor={knowledge_node.mentor_id} | "
                f"Dimension={knowledge_node.dimension} | "
                f"Weight={knowledge_node.weight_score:.2f}"
            )
            
            return knowledge_node
            
        except Exception as e:
            self.stats["failed"] += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"❌ Pipeline failed after {execution_time:.2f}s: {str(e)}",
                exc_info=True
            )
            raise
    
    def process_batch(
        self,
        raw_reviews: List[RawReview],
        continue_on_error: bool = True
    ) -> List[StructuredKnowledgeNode]:
        """
        批量处理评价数据
        
        Args:
            raw_reviews: 原始评价数据列表
            continue_on_error: 是否在遇到错误时继续处理
        
        Returns:
            List[StructuredKnowledgeNode]: 结构化知识节点列表
        """
        logger.info(f"Starting batch processing of {len(raw_reviews)} reviews...")
        
        results = []
        for i, raw_review in enumerate(raw_reviews, 1):
            try:
                logger.info(f"Processing review {i}/{len(raw_reviews)}...")
                node = self.process_raw_review(raw_review)
                results.append(node)
            except Exception as e:
                logger.error(f"Failed to process review {i}: {str(e)}")
                if not continue_on_error:
                    raise
        
        logger.info(
            f"Batch processing completed: {len(results)}/{len(raw_reviews)} successful"
        )
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取流水线统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        success_rate = (
            self.stats["successful"] / self.stats["total_processed"]
            if self.stats["total_processed"] > 0
            else 0.0
        )
        
        return {
            **self.stats,
            "success_rate": success_rate
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "verification_passes": 0,
            "verification_failures": 0
        }
        logger.info("Statistics reset")
