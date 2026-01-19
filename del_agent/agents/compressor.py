"""
结构化压缩智能体 (CompressorAgent)
负责将处理后的信息映射到标准化的知识节点结构
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from ..core.base_agent import BaseAgent
    from ..core.llm_adapter import LLMProvider
    from ..models.schemas import CompressionResult, StructuredKnowledgeNode
except (ImportError, ValueError):
    from core.base_agent import BaseAgent
    from core.llm_adapter import LLMProvider
    from models.schemas import CompressionResult, StructuredKnowledgeNode

logger = logging.getLogger(__name__)


class CompressorAgent(BaseAgent):
    """
    结构化压缩智能体
    
    功能：
    1. 将处理后的信息映射到 StructuredKnowledgeNode
    2. 提取维度标签（Funding、Personality、Academic_Geng 等）
    3. 压缩冗余信息，保留核心内容
    4. 输出：CompressionResult
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        name: str = "CompressorAgent",
        **kwargs
    ):
        """
        初始化结构化压缩智能体
        
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
        return "compressor"
    
    def get_output_schema(self):
        """返回输出数据的Schema"""
        return CompressionResult
    
    def extract_dimension(self, keywords: List[str], content: str) -> str:
        """
        根据关键词和内容提取评价维度
        
        维度映射规则：
        - Funding: 经费、资金、津贴、工资、补贴
        - Personality: 性格、脾气、态度、为人
        - Academic_Geng: 学术梗、黑话、特色
        - Work_Pressure: 压力、加班、工作强度
        - Lab_Atmosphere: 实验室氛围、团队、气氛
        - Publication: 发表、论文、成果
        - Career_Development: 发展、前景、就业
        - Equipment: 设备、仪器、条件
        - Other: 其他
        
        Args:
            keywords: 关键词列表
            content: 内容文本
        
        Returns:
            str: 维度标签
        """
        # 维度关键词映射
        dimension_keywords = {
            "Funding": ["经费", "资金", "津贴", "工资", "补贴", "奖学金", "钱"],
            "Personality": ["性格", "脾气", "态度", "为人", "人品", "风格"],
            "Academic_Geng": ["学术", "梗", "黑话", "特色", "风格", "妲己", "画饼"],
            "Work_Pressure": ["压力", "加班", "工作强度", "忙", "累", "任务"],
            "Lab_Atmosphere": ["实验室", "氛围", "团队", "气氛", "环境", "关系"],
            "Publication": ["发表", "论文", "成果", "文章", "投稿", "审稿"],
            "Career_Development": ["发展", "前景", "就业", "职业", "出路", "前途"],
            "Equipment": ["设备", "仪器", "条件", "硬件", "实验条件"]
        }
        
        # 统计每个维度的匹配分数
        dimension_scores = {dim: 0 for dim in dimension_keywords.keys()}
        
        # 在关键词中匹配
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for dimension, dim_keywords in dimension_keywords.items():
                if any(dim_kw in keyword_lower for dim_kw in dim_keywords):
                    dimension_scores[dimension] += 2  # 关键词匹配权重更高
        
        # 在内容中匹配
        content_lower = content.lower()
        for dimension, dim_keywords in dimension_keywords.items():
            for dim_kw in dim_keywords:
                if dim_kw in content_lower:
                    dimension_scores[dimension] += 1
        
        # 返回得分最高的维度
        max_score = max(dimension_scores.values())
        if max_score == 0:
            return "Other"
        
        for dimension, score in dimension_scores.items():
            if score == max_score:
                return dimension
        
        return "Other"
    
    def compress_content(self, content: str, max_length: int = 200) -> str:
        """
        压缩内容，保留核心信息
        
        简单策略：
        1. 移除重复内容
        2. 截断过长文本
        3. 保留关键信息
        
        Args:
            content: 原始内容
            max_length: 最大长度
        
        Returns:
            str: 压缩后的内容
        """
        # 去除多余空白
        content = " ".join(content.split())
        
        # 如果内容已经足够短，直接返回
        if len(content) <= max_length:
            return content
        
        # 简单截断（实际应用中可以使用更智能的摘要算法）
        compressed = content[:max_length]
        
        # 尝试在句子边界截断
        sentence_endings = ["。", "！", "？", ".", "!", "?"]
        for i in range(len(compressed) - 1, max(0, len(compressed) - 20), -1):
            if compressed[i] in sentence_endings:
                compressed = compressed[:i + 1]
                break
        
        return compressed
    
    def extract_mentor_id(self, source_metadata: Dict[str, Any]) -> str:
        """
        从元数据中提取导师ID
        
        Args:
            source_metadata: 来源元数据
        
        Returns:
            str: 导师ID
        """
        # 尝试从元数据中获取导师ID
        mentor_id = source_metadata.get("mentor_id")
        if mentor_id:
            return str(mentor_id)
        
        # 尝试从标签中提取
        mentor_name = source_metadata.get("mentor_name")
        if mentor_name:
            # 简单处理：去除空格并转小写
            return f"mentor_{mentor_name.replace(' ', '_').lower()}"
        
        # 默认值
        return "mentor_unknown"
    
    def prepare_input(self, raw_input: Any) -> Dict[str, Any]:
        """
        准备输入数据
        
        Args:
            raw_input: 原始输入（字典格式）
        
        Returns:
            Dict[str, Any]: 处理后的输入数据
        """
        if isinstance(raw_input, dict):
            return raw_input
        else:
            raise ValueError(f"Unsupported input type: {type(raw_input)}")
    
    def process(self, raw_input: Any, **kwargs) -> CompressionResult:
        """
        处理数据并生成结构化知识节点
        
        期望输入字段：
        - factual_content: 事实内容（必需）
        - weight_score: 权重评分（必需）
        - keywords: 关键词列表（必需）
        - original_nuance: 原文特色（可选）
        - source_metadata: 来源元数据（可选）
        
        Args:
            raw_input: 原始输入（字典）
            **kwargs: 其他参数
        
        Returns:
            CompressionResult: 压缩结果
        """
        start_time = datetime.now()
        
        try:
            # 准备输入
            input_data = self.prepare_input(raw_input)
            
            # 提取必需字段
            factual_content = input_data.get("factual_content", "")
            weight_score = input_data.get("weight_score", 0.5)
            keywords = input_data.get("keywords", [])
            original_nuance = input_data.get("original_nuance", "")
            source_metadata = input_data.get("source_metadata", {})
            
            # 验证必需字段
            if not factual_content:
                raise ValueError("factual_content is required")
            
            # 提取导师ID
            mentor_id = self.extract_mentor_id(source_metadata)
            
            # 提取维度
            dimension = self.extract_dimension(keywords, factual_content)
            
            # 压缩内容
            fact_content = self.compress_content(factual_content)
            
            # 计算压缩比
            original_length = len(factual_content)
            compressed_length = len(fact_content)
            compression_ratio = compressed_length / original_length if original_length > 0 else 1.0
            
            # 构建结构化知识节点
            knowledge_node = StructuredKnowledgeNode(
                mentor_id=mentor_id,
                dimension=dimension,
                fact_content=fact_content,
                original_nuance=original_nuance,
                weight_score=weight_score,
                tags=keywords,
                last_updated=datetime.now()
            )
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            result = CompressionResult(
                structured_node=knowledge_node,
                compression_ratio=compression_ratio,
                success=True,
                execution_time=execution_time
            )
            
            logger.info(
                f"{self.name} completed: mentor_id={mentor_id}, "
                f"dimension={dimension}, compression_ratio={compression_ratio:.2f}"
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"{self.name} error: {str(e)}", exc_info=True)
            
            # 返回错误结果
            default_node = StructuredKnowledgeNode(
                mentor_id="mentor_error",
                dimension="Other",
                fact_content="处理失败",
                original_nuance="",
                weight_score=0.0,
                tags=[],
                last_updated=datetime.now()
            )
            
            return CompressionResult(
                structured_node=default_node,
                compression_ratio=0.0,
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
