"""
Persona Agent - 个性化对话智能体
负责根据用户画像生成个性化的对话回复

版本：1.0.0
创建：Phase 3.3
"""

from typing import Any, Dict, Optional, Type, List, Callable
import logging
import json
from pydantic import BaseModel

try:
    from ..core.base_agent import BaseAgent
    from ..models.schemas import PersonaResponse, UserPersonalityVector
    from ..core.prompt_manager import PromptManager
except (ImportError, ValueError):
    from core.base_agent import BaseAgent
    from models.schemas import PersonaResponse, UserPersonalityVector
    from core.prompt_manager import PromptManager


class PersonaAgent(BaseAgent):
    """
    个性化对话智能体
    
    功能：
    1. 根据用户画像调整回复风格
    2. 生成符合用户偏好的对话回复
    3. 支持多轮对话的上下文理解
    4. 集成 RAG 结果提供准确信息
    
    工作流程：
    Query + UserProfile + History + RAG → Style Modulation → Personalized Response
    
    使用场景：
    - 前端对话交互
    - 用户咨询回复
    - 个性化信息推荐
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
        初始化个性化对话智能体
        
        Args:
            llm_provider: LLM提供者
            prompt_manager: 提示词管理器（可选）
            trace_enabled: 是否启用 trace 输出
            trace_print: 自定义 trace 输出函数
            **kwargs: 其他配置参数
        """
        super().__init__(
            name="PersonaAgent",
            llm_provider=llm_provider,
            prompt_manager=prompt_manager,
            **kwargs
        )
        
        self.logger = logging.getLogger(f"{__name__}.PersonaAgent")
        self.logger.info("PersonaAgent initialized")

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
        self._trace_print(f"[Persona] {title}: {self._truncate(compact, 280)}")

    async def process(self, raw_input: Any, **kwargs) -> PersonaResponse:
        """
        处理输入数据，带 trace 输出
        """
        import time
        start_time = time.time()

        # 提取查询内容用于 trace
        if isinstance(raw_input, dict):
            query = raw_input.get('query', raw_input.get('user_input', ''))
            rag_results = raw_input.get('rag_results', [])
        else:
            query = str(raw_input)
            rag_results = []
        self._trace("input", {
            "query": self._truncate(query, 160),
            "rag_count": len(rag_results) if isinstance(rag_results, list) else 0
        })

        # 调用父类方法
        result = await super().process(raw_input, **kwargs)

        # Trace 输出
        execution_time = time.time() - start_time
        self._trace("output", {
            "response": self._truncate(result.response_text, 200),
            "style": result.applied_style,
            "time": f"{execution_time:.2f}s"
        })

        return result
    
    def get_output_schema(self) -> Type[BaseModel]:
        """获取输出模式"""
        return PersonaResponse
    
    def get_prompt_template_name(self) -> str:
        """获取提示词模板名称"""
        return "persona"
    
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
            query = raw_input.get('query', raw_input.get('user_input', ''))
            user_profile = raw_input.get('user_profile')
            conversation_history = raw_input.get('conversation_history', [])
            rag_context = raw_input.get('rag_context', '')
        elif isinstance(raw_input, str):
            query = raw_input
            user_profile = kwargs.get('user_profile')
            conversation_history = kwargs.get('conversation_history', [])
            rag_context = kwargs.get('rag_context', '')
        else:
            query = str(raw_input)
            user_profile = None
            conversation_history = []
            rag_context = ''
        
        # 如果没有提供用户画像或是字典，使用默认值或转换
        if user_profile is None:
            user_profile = UserPersonalityVector(user_id="default")
        elif isinstance(user_profile, dict):
            # 如果是字典，尝试转换为UserPersonalityVector对象
            try:
                user_profile = UserPersonalityVector(**user_profile)
            except Exception:
                user_profile = UserPersonalityVector(user_id="default")
        
        # 提取风格参数
        style_params = {
            'humor_level': user_profile.humor_preference,
            'formality_level': user_profile.formality_level,
            'detail_level': user_profile.detail_preference,
            'language_style': user_profile.language_style,
            'preferred_topics': user_profile.preferred_topics,
            'interaction_count': user_profile.interaction_history_count,
        }
        
        input_data = {
            'query': query,
            'conversation_history': conversation_history or [],
            'rag_context': rag_context or "",
            **style_params
        }
        
        self.logger.debug(f"Prepared input for query: {query[:50] if query else ''}...")
        return input_data
    
    def validate_output(self, output: PersonaResponse) -> bool:
        """
        验证输出数据
        
        Args:
            output: 输出数据
            
        Returns:
            是否验证通过
        """
        # 检查回复文本是否为空（允许空响应，但记录警告）
        if not output.response_text or not output.response_text.strip():
            self.logger.warning("Response text is empty")
            # 不返回 False，允许继续
        
        # 检查回复长度是否合理（不应过长）
        response_length = len(output.response_text) if output.response_text else 0
        
        if response_length > 5000:
            self.logger.warning(f"Response too long: {response_length} characters")
            # 也不强制失败，只是警告
        
        return True
    
    def generate_response(
        self,
        query: str,
        user_profile: Optional[UserPersonalityVector] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        rag_context: Optional[str] = None,
        **kwargs
    ) -> PersonaResponse:
        """
        生成个性化回复（便捷方法）
        
        Args:
            query: 用户查询
            user_profile: 用户画像
            conversation_history: 对话历史
            rag_context: RAG 背景信息
            **kwargs: 其他参数
            
        Returns:
            个性化回复结果
        """
        return self.process(
            raw_input=query,
            user_profile=user_profile,
            conversation_history=conversation_history,
            rag_context=rag_context,
            **kwargs
        )
    
    def adjust_style_by_feedback(
        self,
        user_profile: UserPersonalityVector,
        feedback: str
    ) -> Dict[str, float]:
        """
        根据反馈调整风格参数（辅助方法）
        
        Args:
            user_profile: 当前用户画像
            feedback: 用户反馈
            
        Returns:
            调整后的风格参数建议
        """
        adjustments = {}
        feedback_lower = feedback.lower()
        
        # 分析反馈关键词
        if '太正式' in feedback_lower or 'too formal' in feedback_lower:
            adjustments['formality_level'] = max(0.0, user_profile.formality_level - 0.1)
        elif '太随意' in feedback_lower or 'too casual' in feedback_lower:
            adjustments['formality_level'] = min(1.0, user_profile.formality_level + 0.1)
        
        if '太严肃' in feedback_lower or 'too serious' in feedback_lower:
            adjustments['humor_preference'] = min(1.0, user_profile.humor_preference + 0.1)
        elif '太幽默' in feedback_lower or 'too funny' in feedback_lower:
            adjustments['humor_preference'] = max(0.0, user_profile.humor_preference - 0.1)
        
        if '太简单' in feedback_lower or 'too brief' in feedback_lower:
            adjustments['detail_preference'] = min(1.0, user_profile.detail_preference + 0.1)
        elif '太详细' in feedback_lower or 'too detailed' in feedback_lower:
            adjustments['detail_preference'] = max(0.0, user_profile.detail_preference - 0.1)
        
        self.logger.info(f"Style adjustments based on feedback: {adjustments}")
        return adjustments
