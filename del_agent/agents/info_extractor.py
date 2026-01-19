"""
InfoExtractor Agent - 信息提取智能体
负责从用户对话中识别意图并提取结构化信息

版本：1.0.0
创建：Phase 3.4
"""

from typing import Any, Dict, Optional, Type, List, Callable
import logging
import json
from pydantic import BaseModel

try:
    from ..core.base_agent import BaseAgent
    from ..models.schemas import InfoExtractResult, RawReview
    from ..core.prompt_manager import PromptManager
except (ImportError, ValueError):
    from core.base_agent import BaseAgent
    from models.schemas import InfoExtractResult, RawReview
    from core.prompt_manager import PromptManager


class InfoExtractorAgent(BaseAgent):
    """
    信息提取智能体
    
    功能：
    1. 识别用户意图（闲聊/查询/提供信息）
    2. 从对话中提取实体信息（导师名、学校、维度等）
    3. 将用户提供的评价转换为 RawReview 结构
    4. 判断是否需要进一步澄清
    
    工作流程：
    User Input + History → Intent Recognition → Entity Extraction → InfoExtractResult
    
    使用场景：
    - 前端对话路由决策
    - 用户输入分类
    - 信息收集和结构化
    """
    
    def __init__(
        self,
        llm_provider,
        prompt_manager: Optional[PromptManager] = None,
        trace_enabled: bool = False,
        trace_print: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        初始化信息提取智能体
        
        Args:
            llm_provider: LLM提供者
            prompt_manager: 提示词管理器（可选）
            trace_enabled: 是否启用 trace 输出
            trace_print: 自定义 trace 输出函数
            **kwargs: 其他配置参数
        """
        super().__init__(
            name="InfoExtractorAgent",
            llm_provider=llm_provider,
            prompt_manager=prompt_manager,
            **kwargs
        )
        
        self.logger = logging.getLogger(f"{__name__}.InfoExtractorAgent")
        self.logger.info("InfoExtractorAgent initialized")
        
        # Trace 配置
        self.trace_enabled = trace_enabled
        self._trace_print = trace_print or print

    def _truncate(self, text: str, max_len: int = 120) -> str:
        if text is None:
            return ""
        text = str(text).replace("\n", " ")
        return text if len(text) <= max_len else (text[: max_len - 3] + "...")

    def _trace(self, title: str, payload: Dict[str, Any]):
        if not self.trace_enabled:
            return
        try:
            compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
        except Exception:
            compact = str(payload)
        self._trace_print(f"[InfoExtractor] {title}: {self._truncate(compact, 280)}")

    async def process(self, raw_input: Any, **kwargs) -> InfoExtractResult:
        """
        处理输入数据，带 trace 输出
        """
        import time
        start_time = time.time()

        # Trace 输入
        if isinstance(raw_input, dict):
            user_input = raw_input.get('user_input', '')
        else:
            user_input = str(raw_input)
        self._trace("input", {"user_input": self._truncate(user_input, 160)})

        # 调用父类方法
        result = await super().process(raw_input, **kwargs)

        # Trace 输出
        execution_time = time.time() - start_time
        self._trace("output", {
            "intent_type": result.intent_type,
            "confidence": result.confidence_score,
            "entities": result.extracted_entities,
            "has_review": bool(result.extracted_review),
            "time": f"{execution_time:.2f}s"
        })

        return result
        
    # 定义支持的评价维度
    valid_dimensions = [
        "Funding", "Personality", "Academic_Geng",
        "Work_Pressure", "Lab_Atmosphere", "Publication",
        "Career_Development", "Equipment", "Other"
    ]
    
    def get_output_schema(self) -> Type[BaseModel]:
        """获取输出模式"""
        return InfoExtractResult
    
    def get_prompt_template_name(self) -> str:
        """获取提示词模板名称"""
        return "info_extractor"
    
    def prepare_input(
        self,
        raw_input: Any,
        **kwargs
    ) -> Dict[str, Any]:
        """
        准备输入数据
        
        Args:
            raw_input: 原始输入（可以是字符串或字典）
            **kwargs: 其他参数
            
        Returns:
            处理后的输入数据字典
        """
        # 处理不同的输入格式
        if isinstance(raw_input, dict):
            user_input = raw_input.get('user_input', '')
            conversation_history = raw_input.get('conversation_history', [])
        elif isinstance(raw_input, str):
            user_input = raw_input
            conversation_history = kwargs.get('conversation_history', [])
        else:
            user_input = str(raw_input)
            conversation_history = []
        
        input_data = {
            'user_input': user_input,
            'conversation_history': conversation_history
        }
        
        self.logger.debug(f"Prepared input for extraction: {user_input[:100]}...")
        return input_data
    
    def validate_output(self, output: InfoExtractResult) -> bool:
        """
        验证输出数据
        
        Args:
            output: 输出数据
            
        Returns:
            是否验证通过
        """
        # 检查意图类型是否有效
        valid_intents = ["chat", "query", "provide_info"]
        if output.intent_type not in valid_intents:
            self.logger.warning(f"Invalid intent type: {output.intent_type}")
            return False
        
        # 如果是提供信息，应该有提取的评价内容
        if output.intent_type == "provide_info":
            if output.extracted_review is None:
                self.logger.warning("provide_info intent but no extracted_review")
                # 不强制失败，允许只提取实体
        
        # 检查置信度范围
        if not 0 <= output.confidence_score <= 1:
            self.logger.warning(f"Invalid confidence score: {output.confidence_score}")
            return False
        
        return True
    
    def extract_info(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> InfoExtractResult:
        """
        从用户输入中提取信息（便捷方法）
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            **kwargs: 其他参数
            
        Returns:
            信息提取结果
        """
        return self.process(
            raw_input=user_input,
            conversation_history=conversation_history,
            **kwargs
        )
    
    def post_process_result(self, result: InfoExtractResult) -> InfoExtractResult:
        """
        后处理提取结果
        
        Args:
            result: 原始提取结果
            
        Returns:
            后处理后的结果
        """
        # 标准化维度名称
        if result.extracted_entities.get('dimension'):
            dimension = result.extracted_entities['dimension']
            if dimension not in self.valid_dimensions:
                # 尝试映射常见别名
                dimension_mapping = {
                    '经费': 'Funding',
                    '资金': 'Funding',
                    '性格': 'Personality',
                    '人品': 'Personality',
                    '压力': 'Work_Pressure',
                    '工作强度': 'Work_Pressure',
                    '氛围': 'Lab_Atmosphere',
                    '环境': 'Lab_Atmosphere',
                    '论文': 'Publication',
                    '发表': 'Publication',
                    '发展': 'Career_Development',
                    '前途': 'Career_Development',
                    '设备': 'Equipment',
                    '耿直': 'Academic_Geng',
                    '画饼': 'Academic_Geng',
                }
                
                for key, value in dimension_mapping.items():
                    if key in dimension:
                        result.extracted_entities['dimension'] = value
                        self.logger.debug(f"Mapped dimension '{dimension}' to '{value}'")
                        break
                else:
                    result.extracted_entities['dimension'] = 'Other'
                    self.logger.debug(f"Unknown dimension '{dimension}', mapped to 'Other'")
        
        # 如果置信度过低，标记需要澄清
        if result.confidence_score < 0.5:
            result.requires_clarification = True
            if not result.clarification_questions:
                result.clarification_questions = [
                    "抱歉，我没有完全理解您的意思，能否详细说明一下？"
                ]
        
        return result
    
    def classify_intent(self, user_input: str) -> str:
        """
        快速意图分类（规则基础，用于备用）
        
        Args:
            user_input: 用户输入
            
        Returns:
            意图类型
        """
        user_input_lower = user_input.lower()
        
        # 闲聊关键词
        chat_keywords = ['你好', '谢谢', '再见', 'hello', 'hi', 'thanks', 'bye']
        if any(kw in user_input_lower for kw in chat_keywords) and len(user_input) < 20:
            return "chat"
        
        # 查询关键词
        query_keywords = ['怎么样', '如何', '吗', '？', '?', '介绍', '了解', '请问']
        if any(kw in user_input for kw in query_keywords):
            return "query"
        
        # 提供信息关键词（通常是陈述句）
        provide_keywords = ['我的', '我们', '导师', '老师', '很', '非常', '比较']
        if any(kw in user_input for kw in provide_keywords) and len(user_input) > 15:
            return "provide_info"
        
        # 默认为查询
        return "query"


class InfoExtractionHelper:
    """
    信息提取辅助类
    提供一些静态方法用于信息处理
    """
    
    @staticmethod
    def merge_entities(
        entities1: Dict[str, Any],
        entities2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并两个实体字典
        
        Args:
            entities1: 第一个实体字典
            entities2: 第二个实体字典
            
        Returns:
            合并后的实体字典
        """
        merged = entities1.copy()
        
        for key, value in entities2.items():
            if key not in merged or not merged[key]:
                merged[key] = value
            elif isinstance(value, list) and isinstance(merged[key], list):
                # 合并列表，去重
                merged[key] = list(set(merged[key] + value))
        
        return merged
    
    @staticmethod
    def extract_mentor_names(text: str) -> List[str]:
        """
        从文本中提取可能的导师名称
        
        Args:
            text: 输入文本
            
        Returns:
            导师名称列表
        """
        import re
        
        # 简单的正则匹配（实际应使用NER）
        patterns = [
            r'([一-龥]{2,4})(老师|教授|导师)',
            r'(Prof\.|Professor|Dr\.)\s+([A-Z][a-z]+)',
        ]
        
        names = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    name = ''.join(match).replace('老师', '').replace('教授', '').replace('导师', '')
                    name = name.replace('Prof.', '').replace('Professor', '').replace('Dr.', '').strip()
                    if name:
                        names.append(name)
        
        return list(set(names))
