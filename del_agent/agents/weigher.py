"""
权重分析智能体 (WeigherAgent)
负责计算评价信息的可信度权重
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

try:
    from ..core.base_agent import BaseAgent
    from ..core.llm_adapter import LLMProvider
    from ..models.schemas import WeightAnalysisResult, RawReview
except (ImportError, ValueError):
    from core.base_agent import BaseAgent
    from core.llm_adapter import LLMProvider
    from models.schemas import WeightAnalysisResult, RawReview

logger = logging.getLogger(__name__)


class WeigherAgent(BaseAgent):
    """
    权重分析智能体
    
    功能：
    1. 计算信息可信度评分
    2. 算法：Score = f(IdentityConfidence, TimeDecay, OutlierStatus)
    3. 输出：WeightAnalysisResult
    
    权重计算公式：
        base_score = identity_confidence * 0.5 + time_decay * 0.3
        outlier_penalty = 0.2 if outlier_status else 0
        final_score = max(0, base_score - outlier_penalty)
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        name: str = "WeigherAgent",
        **kwargs
    ):
        """
        初始化权重分析智能体
        
        Args:
            llm_provider: LLM提供者实例
            name: 智能体名称
            **kwargs: 其他参数
        """
        super().__init__(
            name=name,
            llm_provider=llm_provider,
            **kwargs
        )
        logger.info(f"{self.name} initialized")
    
    def get_prompt_template_name(self) -> str:
        """返回提示词模板名称"""
        return "weigher"
    
    def get_output_schema(self):
        """返回输出数据的Schema"""
        return WeightAnalysisResult
    
    def calculate_weight(
        self,
        identity_confidence: float,
        time_decay: float,
        outlier_status: bool
    ) -> float:
        """
        权重计算公式
        
        Args:
            identity_confidence: 身份可信度 (0-1)
            time_decay: 时间衰减因子 (0-1)
            outlier_status: 是否为离群点
        
        Returns:
            float: 综合权重评分 (0-1)
        
        Formula:
            base_score = identity_confidence * 0.5 + time_decay * 0.3
            outlier_penalty = 0.2 if outlier_status else 0
            final_score = max(0, min(1, base_score - outlier_penalty))
        """
        # 基础评分：身份可信度占50%，时间衰减占30%
        base_score = identity_confidence * 0.5 + time_decay * 0.3
        
        # 离群点惩罚：如果是离群点，减20%
        outlier_penalty = 0.2 if outlier_status else 0
        
        # 最终评分：确保在[0, 1]范围内
        final_score = max(0.0, min(1.0, base_score - outlier_penalty))
        
        return final_score
    
    def calculate_identity_confidence(
        self,
        source_metadata: Dict[str, Any]
    ) -> float:
        """
        计算身份可信度
        
        规则：
        1. 实名认证：+0.3
        2. 学生/校友身份：+0.3
        3. 账号活跃度：+0.2
        4. 历史可信记录：+0.2
        
        Args:
            source_metadata: 来源元数据
        
        Returns:
            float: 身份可信度 (0-1)
        """
        confidence = 0.0
        
        # 实名认证
        if source_metadata.get("verified", False):
            confidence += 0.3
        
        # 身份验证（学生/校友）
        identity = source_metadata.get("identity", "")
        if identity in ["student", "alumni"]:
            confidence += 0.3
        elif identity == "verified_user":
            confidence += 0.2
        else:
            confidence += 0.1  # 基础分
        
        # 账号活跃度（基于发帖数量）
        post_count = source_metadata.get("post_count", 0)
        if post_count > 100:
            confidence += 0.2
        elif post_count > 50:
            confidence += 0.15
        elif post_count > 10:
            confidence += 0.1
        else:
            confidence += 0.05
        
        # 历史可信记录（基于信誉分）
        reputation = source_metadata.get("reputation", 0)
        if reputation > 1000:
            confidence += 0.2
        elif reputation > 500:
            confidence += 0.15
        elif reputation > 100:
            confidence += 0.1
        else:
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def calculate_time_decay(
        self,
        timestamp: datetime,
        half_life_days: int = 180
    ) -> float:
        """
        计算时间衰减因子
        
        使用指数衰减模型：decay = 2^(-days_elapsed / half_life_days)
        
        Args:
            timestamp: 数据时间戳
            half_life_days: 半衰期（天数），默认180天（6个月）
        
        Returns:
            float: 时间衰减因子 (0-1)
        """
        now = datetime.now()
        
        # 计算经过的天数
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        days_elapsed = (now - timestamp).days
        
        # 如果是未来的时间戳，返回1.0
        if days_elapsed < 0:
            return 1.0
        
        # 指数衰减公式
        decay = 2 ** (-days_elapsed / half_life_days)
        
        return max(0.0, min(1.0, decay))
    
    def detect_outlier(
        self,
        content: str,
        similar_reviews: Optional[list] = None
    ) -> bool:
        """
        检测是否为离群点/异常值
        
        简单规则：
        1. 极端情绪表达（大量感叹号、全大写）
        2. 内容过短（< 10字）或过长（> 500字）
        3. 与其他评价显著不一致（如果提供了similar_reviews）
        
        Args:
            content: 评论内容
            similar_reviews: 相似评论列表（可选）
        
        Returns:
            bool: 是否为离群点
        """
        # 规则1：极端情绪表达
        exclamation_count = content.count('！') + content.count('!')
        if exclamation_count > 5:
            return True
        
        if content.isupper() and len(content) > 10:
            return True
        
        # 规则2：内容长度异常
        content_length = len(content.strip())
        if content_length < 10 or content_length > 500:
            return True
        
        # 规则3：与其他评价不一致（简化版：检查是否包含特定关键词）
        # 实际应用中可以使用语义相似度计算
        if similar_reviews:
            # 这里简化处理，实际可以使用向量相似度
            pass
        
        return False
    
    def prepare_input(self, raw_input: Any) -> Dict[str, Any]:
        """
        准备输入数据
        
        Args:
            raw_input: 原始输入（可以是RawReview或字典）
        
        Returns:
            Dict[str, Any]: 处理后的输入数据
        """
        if isinstance(raw_input, RawReview):
            return {
                "content": raw_input.content,
                "source_metadata": raw_input.source_metadata,
                "timestamp": raw_input.timestamp
            }
        elif isinstance(raw_input, dict):
            return raw_input
        else:
            raise ValueError(f"Unsupported input type: {type(raw_input)}")
    
    def process(self, raw_input: Any, **kwargs) -> WeightAnalysisResult:
        """
        处理评价数据并计算权重
        
        Args:
            raw_input: 原始输入（RawReview或包含必要字段的字典）
            **kwargs: 其他参数
        
        Returns:
            WeightAnalysisResult: 权重分析结果
        """
        start_time = datetime.now()
        
        try:
            # 准备输入
            input_data = self.prepare_input(raw_input)
            
            content = input_data.get("content", "")
            source_metadata = input_data.get("source_metadata", {})
            timestamp = input_data.get("timestamp", datetime.now())
            
            # 计算各个维度的指标
            identity_confidence = self.calculate_identity_confidence(source_metadata)
            time_decay = self.calculate_time_decay(timestamp)
            outlier_status = self.detect_outlier(content)
            
            # 计算综合权重
            weight_score = self.calculate_weight(
                identity_confidence=identity_confidence,
                time_decay=time_decay,
                outlier_status=outlier_status
            )
            
            # 生成推理说明
            reasoning_parts = []
            reasoning_parts.append(f"身份可信度: {identity_confidence:.2f}")
            reasoning_parts.append(f"时间衰减: {time_decay:.2f}")
            if outlier_status:
                reasoning_parts.append("检测到异常特征（离群点）")
            reasoning = ", ".join(reasoning_parts)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            result = WeightAnalysisResult(
                weight_score=weight_score,
                identity_confidence=identity_confidence,
                time_decay=time_decay,
                outlier_status=outlier_status,
                reasoning=reasoning,
                success=True,
                execution_time=execution_time
            )
            
            logger.info(
                f"{self.name} completed: weight_score={weight_score:.2f}, "
                f"reasoning={reasoning}"
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"{self.name} error: {str(e)}", exc_info=True)
            
            return WeightAnalysisResult(
                weight_score=0.5,  # 默认中等权重
                identity_confidence=0.5,
                time_decay=0.5,
                outlier_status=False,
                reasoning=f"处理失败: {str(e)}",
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
