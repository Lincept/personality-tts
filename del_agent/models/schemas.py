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