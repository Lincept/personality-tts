"""
Data models for AI Data Factory
定义项目中使用的所有Pydantic数据模型
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class CommentCleaningResult(BaseModel):
    """
    评论清洗结果模型
    用于RawCommentCleaner智能体的输出
    """
    factual_content: str = Field(
        ..., 
        description="去除情绪后的事实内容",
        example="经费充足，津贴发放少"
    )
    emotional_intensity: float = Field(
        ..., 
        description="情绪强度评分，0-1之间",
        ge=0.0, 
        le=1.0,
        example=0.8
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="提取的关键标签列表",
        example=["经费", "津贴", "学术妲己"]
    )
    success: bool = Field(default=True, description="处理是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    execution_time: float = Field(default=0.0, description="执行时间（秒）")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    @validator('emotional_intensity')
    def validate_emotional_intensity(cls, v):
        """验证情绪强度范围"""
        if not 0 <= v <= 1:
            raise ValueError('emotional_intensity must be between 0 and 1')
        return v
    
    @validator('keywords')
    def validate_keywords(cls, v):
        """验证关键词列表"""
        if not isinstance(v, list):
            raise ValueError('keywords must be a list')
        return [str(keyword).strip() for keyword in v if keyword]


class ProcessingStats(BaseModel):
    """
    处理统计信息模型
    """
    total_items: int = Field(default=0, description="处理项目总数")
    successful_items: int = Field(default=0, description="成功处理项目数")
    failed_items: int = Field(default=0, description="失败处理项目数")
    total_execution_time: float = Field(default=0.0, description="总执行时间（秒）")
    average_execution_time: float = Field(default=0.0, description="平均执行时间（秒）")
    success_rate: float = Field(default=0.0, description="成功率")
    
    @validator('success_rate')
    def validate_success_rate(cls, v):
        """验证成功率范围"""
        if not 0 <= v <= 1:
            raise ValueError('success_rate must be between 0 and 1')
        return v


class LLMConfig(BaseModel):
    """
    LLM配置模型
    """
    provider: str = Field(..., description="提供者名称")
    model_name: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    api_secret: Optional[str] = Field(default=None, description="API密钥（用于豆包等需要双密钥的服务商）")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    timeout: int = Field(default=30, description="超时时间（秒）")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    temperature: float = Field(default=0.7, description="温度参数")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        """验证温度参数范围"""
        if not 0 <= v <= 2:
            raise ValueError('temperature must be between 0 and 2')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """验证超时时间"""
        if v <= 0:
            raise ValueError('timeout must be positive')
        return v


class AgentConfig(BaseModel):
    """
    智能体配置模型
    """
    name: str = Field(..., description="智能体名称")
    description: Optional[str] = Field(default=None, description="智能体描述")
    llm_config: LLMConfig = Field(..., description="LLM配置")
    prompt_template: str = Field(..., description="提示词模板名称")
    max_retries: int = Field(default=3, description="最大重试次数")
    
    @validator('max_retries')
    def validate_max_retries(cls, v):
        """验证重试次数"""
        if v < 0:
            raise ValueError('max_retries must be non-negative')
        return v


# ==================== Phase 1: 新增数据模型 ====================

class RawReview(BaseModel):
    """
    原始评价数据模型
    用于表示从各种来源收集的未处理评论
    """
    content: str = Field(
        ...,
        description="原始评论内容",
        example="这老板简直是'学术妲己'，太会画饼了！"
    )
    source_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="来源元数据（平台、发布者ID等）",
        example={
            "platform": "知乎",
            "author_id": "user_12345",
            "post_id": "post_67890"
        }
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="数据收集时间戳"
    )
    
    @validator('content')
    def validate_content(cls, v):
        """验证内容不为空"""
        if not v or not v.strip():
            raise ValueError('content cannot be empty')
        return v.strip()


class CriticFeedback(BaseModel):
    """
    判别反馈模型
    CriticAgent 用于评估其他 Agent 输出质量的反馈结果
    """
    is_approved: bool = Field(
        ...,
        description="是否通过质量检查",
        example=True
    )
    reasoning: str = Field(
        ...,
        description="判别的详细原因说明",
        example="输出内容准确提取了关键信息，格式符合要求"
    )
    suggestion: str = Field(
        default="",
        description="改进建议（若不通过时提供）",
        example="建议增加对'学术妲己'这一黑话的解释"
    )
    confidence_score: float = Field(
        default=1.0,
        description="判别置信度评分，0-1之间",
        ge=0.0,
        le=1.0,
        example=0.85
    )
    
    @validator('confidence_score')
    def validate_confidence_score(cls, v):
        """验证置信度范围"""
        if not 0 <= v <= 1:
            raise ValueError('confidence_score must be between 0 and 1')
        return v


class StructuredKnowledgeNode(BaseModel):
    """
    结构化知识单元模型
    后端数据工厂处理后的标准化输出
    """
    mentor_id: str = Field(
        ...,
        description="导师/机构唯一标识",
        example="mentor_zhang_san"
    )
    dimension: str = Field(
        ...,
        description="评价维度（Funding/Personality/Academic_Geng等）",
        example="Funding"
    )
    fact_content: str = Field(
        ...,
        description="去极化后的事实内容",
        example="经费充足，但学生津贴发放较少"
    )
    original_nuance: str = Field(
        default="",
        description="保留的原文特色或黑话",
        example="学术妲己，画饼"
    )
    weight_score: float = Field(
        ...,
        description="信息权重/可信度评分，0-1之间",
        ge=0.0,
        le=1.0,
        example=0.75
    )
    tags: List[str] = Field(
        default_factory=list,
        description="相关标签列表",
        example=["经费", "津贴", "学术风格"]
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="最后更新时间"
    )
    
    @validator('weight_score')
    def validate_weight_score(cls, v):
        """验证权重评分范围"""
        if not 0 <= v <= 1:
            raise ValueError('weight_score must be between 0 and 1')
        return v
    
    @validator('dimension')
    def validate_dimension(cls, v):
        """验证维度值"""
        valid_dimensions = [
            "Funding", "Personality", "Academic_Geng",
            "Work_Pressure", "Lab_Atmosphere", "Publication",
            "Career_Development", "Equipment", "Other"
        ]
        if v not in valid_dimensions:
            raise ValueError(f'dimension must be one of {valid_dimensions}')
        return v


class SlangDecodingResult(BaseModel):
    """
    黑话解码结果模型
    SlangDecoderAgent 的输出
    """
    decoded_text: str = Field(
        ...,
        description="解码后的文本",
        example="导师很会承诺但不兑现，经费充足但不发给学生"
    )
    slang_dictionary: Dict[str, str] = Field(
        default_factory=dict,
        description="识别到的黑话词典",
        example={"学术妲己": "善于承诺但不兑现的导师", "画饼": "做出承诺但不实现"}
    )
    confidence_score: float = Field(
        default=1.0,
        description="解码置信度",
        ge=0.0,
        le=1.0,
        example=0.9
    )
    success: bool = Field(default=True, description="处理是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    execution_time: float = Field(default=0.0, description="执行时间（秒）")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="时间戳"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class WeightAnalysisResult(BaseModel):
    """
    权重分析结果模型
    WeigherAgent 的输出
    """
    weight_score: float = Field(
        ...,
        description="综合权重评分，0-1之间",
        ge=0.0,
        le=1.0,
        example=0.78
    )
    identity_confidence: float = Field(
        ...,
        description="身份可信度，0-1之间",
        ge=0.0,
        le=1.0,
        example=0.85
    )
    time_decay: float = Field(
        ...,
        description="时间衰减因子，0-1之间",
        ge=0.0,
        le=1.0,
        example=0.9
    )
    outlier_status: bool = Field(
        ...,
        description="是否为异常值/离群点",
        example=False
    )
    reasoning: str = Field(
        default="",
        description="权重评分的详细推理",
        example="来源可信，时间较新，内容与其他评价一致"
    )
    success: bool = Field(default=True, description="处理是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    execution_time: float = Field(default=0.0, description="执行时间（秒）")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="时间戳"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class CompressionResult(BaseModel):
    """
    结构化压缩结果模型
    CompressorAgent 的输出
    """
    structured_node: StructuredKnowledgeNode = Field(
        ...,
        description="结构化知识节点"
    )
    compression_ratio: float = Field(
        default=0.0,
        description="压缩比例（原文长度/压缩后长度）",
        ge=0.0,
        example=0.3
    )
    success: bool = Field(default=True, description="处理是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    execution_time: float = Field(default=0.0, description="执行时间（秒）")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="时间戳"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")