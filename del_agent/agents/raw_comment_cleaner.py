"""
Raw Comment Cleaner Agent - 原始评论清洗员
用于处理充满情绪和黑话的文本，提取事实内容和关键信息
"""

from typing import Any, Dict, Optional
import logging

from ..core.base_agent import BaseAgent
from ..models.schemas import CommentCleaningResult
from ..core.prompt_manager import PromptManager


class RawCommentCleaner(BaseAgent):
    """
    原始评论清洗智能体
    
    功能：
    1. 识别并量化文本中的情绪强度
    2. 提取去除情绪后的事实内容
    3. 识别关键标签和主题词
    
    输入：包含情绪和黑话的原始文本
    输出：结构化的评论分析结果
    """
    
    def __init__(
        self,
        llm_provider,
        prompt_manager: Optional[PromptManager] = None,
        **kwargs
    ):
        """
        初始化评论清洗智能体
        
        Args:
            llm_provider: LLM提供者
            prompt_manager: 提示词管理器
            **kwargs: 其他配置参数
        """
        super().__init__(
            name="RawCommentCleaner",
            llm_provider=llm_provider,
            prompt_manager=prompt_manager,
            **kwargs
        )
        
        self.logger = logging.getLogger(f"{__name__}.RawCommentCleaner")
        self.logger.info("RawCommentCleaner initialized")
    
    def get_output_schema(self) -> type:
        """获取输出模式"""
        return CommentCleaningResult
    
    def get_prompt_template_name(self) -> str:
        """获取提示词模板名称"""
        return "comment_cleaner"
    
    def prepare_input(self, raw_input: Any, **kwargs) -> Dict[str, Any]:
        """
        准备输入数据
        
        Args:
            raw_input: 原始评论文本
            **kwargs: 其他参数
            
        Returns:
            处理后的输入数据
        """
        # 确保输入是字符串
        if not isinstance(raw_input, str):
            raw_input = str(raw_input)
        
        # 基本文本清理
        cleaned_input = raw_input.strip()
        
        # 构建输入数据
        input_data = {
            "raw_comment": cleaned_input,
            "comment_length": len(cleaned_input),
            "has_chinese": self._contains_chinese(cleaned_input),
            **kwargs
        }
        
        self.logger.debug(f"Prepared input data: comment_length={input_data['comment_length']}")
        return input_data
    
    def validate_output(self, output: CommentCleaningResult) -> bool:
        """
        验证输出数据
        
        Args:
            output: 评论清洗结果
            
        Returns:
            是否验证通过
        """
        try:
            # 基本验证
            if not output.factual_content or not output.factual_content.strip():
                self.logger.warning("Empty factual content in output")
                return False
            
            # 验证情绪强度范围
            if not 0 <= output.emotional_intensity <= 1:
                self.logger.warning(f"Invalid emotional intensity: {output.emotional_intensity}")
                return False
            
            # 验证关键词列表
            if not isinstance(output.keywords, list):
                self.logger.warning("Keywords is not a list")
                return False
            
            # 清理关键词（去除空字符串和重复项）
            cleaned_keywords = list(set(k.strip() for k in output.keywords if k.strip()))
            if len(cleaned_keywords) != len(output.keywords):
                self.logger.info(f"Cleaned keywords: {len(output.keywords)} -> {len(cleaned_keywords)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {str(e)}")
            return False
    
    def _contains_chinese(self, text: str) -> bool:
        """
        检查文本是否包含中文字符
        
        Args:
            text: 文本内容
            
        Returns:
            是否包含中文
        """
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def analyze_batch(self, comments: list, **kwargs) -> list:
        """
        批量分析评论
        
        Args:
            comments: 评论列表
            **kwargs: 其他参数
            
        Returns:
            分析结果列表
        """
        results = []
        total_comments = len(comments)
        
        self.logger.info(f"Starting batch analysis of {total_comments} comments")
        
        for i, comment in enumerate(comments, 1):
            try:
                self.logger.info(f"Processing comment {i}/{total_comments}")
                result = self.process(comment, **kwargs)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Failed to process comment {i}: {str(e)}")
                # 创建错误结果
                error_result = CommentCleaningResult(
                    success=False,
                    error_message=str(e),
                    factual_content="",
                    emotional_intensity=0.0,
                    keywords=[]
                )
                results.append(error_result)
        
        # 统计信息
        successful_count = sum(1 for r in results if r.success)
        self.logger.info(f"Batch analysis completed: {successful_count}/{total_comments} successful")
        
        return results
    
    def get_processing_summary(self, results: list) -> Dict[str, Any]:
        """
        获取处理汇总信息
        
        Args:
            results: 处理结果列表
            
        Returns:
            汇总信息字典
        """
        if not results:
            return {"total": 0, "successful": 0, "failed": 0, "avg_emotional_intensity": 0.0}
        
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        
        # 计算平均情绪强度（仅成功结果）
        successful_results = [r for r in results if r.success]
        avg_emotional_intensity = (
            sum(r.emotional_intensity for r in successful_results) / len(successful_results)
            if successful_results else 0.0
        )
        
        # 汇总关键词
        all_keywords = []
        for result in successful_results:
            all_keywords.extend(result.keywords)
        
        keyword_frequency = {}
        for keyword in all_keywords:
            keyword_frequency[keyword] = keyword_frequency.get(keyword, 0) + 1
        
        # 获取最常见的关键词
        top_keywords = sorted(
            keyword_frequency.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_emotional_intensity": avg_emotional_intensity,
            "top_keywords": top_keywords,
            "unique_keywords": len(keyword_frequency)
        }