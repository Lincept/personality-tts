"""
Frontend Orchestrator - 前端编排器/路由器
负责统一前端交互流程，集成各个智能体并根据用户意图进行路由

版本：1.0.0
创建：Phase 3.5
"""

from typing import Any, Dict, Optional, List, Callable
import logging
import json
from datetime import datetime

try:
    from ..models.schemas import (
        InfoExtractResult,
        PersonaResponse,
        UserPersonalityVector,
        RawReview,
        CompressionResult
    )
    from ..agents.info_extractor import InfoExtractorAgent
    from ..agents.persona import PersonaAgent
    from ..frontend.user_profile import UserProfileManager
    from ..core.llm_adapter import LLMProvider
except (ImportError, ValueError):
    from del_agent.models.schemas import (
        InfoExtractResult,
        PersonaResponse,
        UserPersonalityVector,
        RawReview,
        CompressionResult
    )
    from del_agent.agents.info_extractor import InfoExtractorAgent
    from del_agent.agents.persona import PersonaAgent
    from del_agent.frontend.user_profile import UserProfileManager
    from del_agent.core.llm_adapter import LLMProvider

# DataFactoryPipeline 是可选的（延迟导入）
DataFactoryPipeline = None
try:
    try:
        from ..backend.factory import DataFactoryPipeline
    except (ImportError, ValueError):
        from del_agent.backend.factory import DataFactoryPipeline
except (ImportError, ModuleNotFoundError):
    # Backend not available, will handle None in code
    pass


logger = logging.getLogger(__name__)


class ConversationContext:
    """
    对话上下文管理器
    维护单个用户会话的历史和状态
    """
    
    def __init__(self, user_id: str, max_history: int = 10):
        """
        初始化对话上下文
        
        Args:
            user_id: 用户ID
            max_history: 最大历史记录数
        """
        self.user_id = user_id
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_interaction = datetime.now()
        
    def add_turn(self, user_input: str, assistant_response: str):
        """
        添加一轮对话
        
        Args:
            user_input: 用户输入
            assistant_response: 助手回复
        """
        self.history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        self.history.append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持历史记录在限制内
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]
        
        self.last_interaction = datetime.now()
    
    def get_history_text(self) -> str:
        """
        获取格式化的对话历史
        
        Returns:
            对话历史的文本表示
        """
        if not self.history:
            return ""
        
        history_lines = []
        for turn in self.history:
            role = "用户" if turn["role"] == "user" else "助手"
            history_lines.append(f"{role}: {turn['content']}")
        
        return "\n".join(history_lines)
    
    def clear(self):
        """清空对话历史"""
        self.history = []


class FrontendOrchestrator:
    """
    前端编排器
    
    功能：
    1. 路由用户输入到不同的处理流程
    2. 集成 InfoExtractorAgent、PersonaAgent、DataFactoryPipeline
    3. 管理对话上下文和用户画像
    4. 提供统一的前端接口
    
    工作流程：
    User Input → InfoExtractor (意图识别)
              → 路由决策：
                  - 闲聊：PersonaAgent 直接回复
                  - 查询：PersonaAgent + RAG 检索
                  - 提供信息：提取 RawReview → DataFactoryPipeline → 入库 → PersonaAgent 确认
    
    使用场景：
    - 前端应用的统一入口
    - 多智能体协作编排
    - 会话管理和状态维护
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        profile_manager: Optional[UserProfileManager] = None,
        backend_pipeline: Optional[DataFactoryPipeline] = None,
        enable_rag: bool = False,
        rag_retriever: Optional[Any] = None,
        max_conversation_history: int = 10,
        trace_frontend: bool = False,
        trace_print: Optional[Callable[[str], None]] = None
    ):
        """
        初始化前端编排器
        
        Args:
            llm_provider: LLM提供者实例
            profile_manager: 用户画像管理器（可选，默认创建新实例）
            backend_pipeline: 后端数据工厂流水线（可选，默认创建新实例）
            enable_rag: 是否启用RAG检索
            rag_retriever: RAG检索器实例（可选）
            max_conversation_history: 最大对话历史轮数
        """
        self.llm_provider = llm_provider
        self.enable_rag = enable_rag
        self.rag_retriever = rag_retriever
        self.max_conversation_history = max_conversation_history

        self.trace_frontend = trace_frontend
        self._trace_print = trace_print or print
        
        logger.info("Initializing FrontendOrchestrator...")
        
        # 初始化用户画像管理器
        self.profile_manager = profile_manager or UserProfileManager()
        logger.info("✓ UserProfileManager initialized")
        
        # 初始化智能体（传递 trace 参数）
        self.info_extractor = InfoExtractorAgent(
            llm_provider,
            trace_enabled=trace_frontend,
            trace_print=self._trace_print
        )
        logger.info("✓ InfoExtractorAgent initialized")
        
        self.persona_agent = PersonaAgent(
            llm_provider,
            trace_enabled=trace_frontend,
            trace_print=self._trace_print
        )
        logger.info("✓ PersonaAgent initialized")
        
        # 初始化后端流水线（可选，用于处理用户提供的信息）
        self.backend_pipeline = backend_pipeline
        if self.backend_pipeline:
            logger.info("✓ DataFactoryPipeline initialized")
        else:
            logger.info("! DataFactoryPipeline not provided (info submission disabled)")
        
        # 对话上下文管理
        self.conversations: Dict[str, ConversationContext] = {}
        
        logger.info("✓ FrontendOrchestrator initialized successfully")

    def _truncate(self, text: str, max_len: int = 120) -> str:
        if text is None:
            return ""
        text = str(text).replace("\n", " ")
        return text if len(text) <= max_len else (text[: max_len - 3] + "...")

    def _trace(self, title: str, payload: Dict[str, Any]):
        if not self.trace_frontend:
            return
        try:
            compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
        except Exception:
            compact = str(payload)
        self._trace_print(f"[FRONTEND] {title}: {self._truncate(compact, 300)}")
    
    def get_or_create_context(self, user_id: str) -> ConversationContext:
        """
        获取或创建用户的对话上下文
        
        Args:
            user_id: 用户ID
            
        Returns:
            对话上下文实例
        """
        if user_id not in self.conversations:
            self.conversations[user_id] = ConversationContext(
                user_id, 
                max_history=self.max_conversation_history
            )
        return self.conversations[user_id]
    
    async def process_user_input(
        self,
        user_id: str,
        user_input: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入（主入口）
        
        Args:
            user_id: 用户ID
            user_input: 用户输入文本
            additional_context: 额外的上下文信息（可选）
            
        Returns:
            包含回复和元数据的字典
        """
        start_time = datetime.now()
        
        try:
            # 1. 获取对话上下文和用户画像
            context = self.get_or_create_context(user_id)
            user_profile = self.profile_manager.get_profile(user_id)

            self._trace("Input", {
                "user_id": user_id,
                "user_input": self._truncate(user_input, 160),
                "history_chars": len(context.get_history_text() or "")
            })
            
            # 2. 信息提取和意图识别
            extract_result = await self._extract_intent_and_entities(
                user_input=user_input,
                conversation_history=context.get_history_text(),
                additional_context=additional_context
            )

            intent_type = extract_result.intent_type
            self._trace("InfoExtractor.output", {
                "intent_type": intent_type,
                "confidence_score": getattr(extract_result, "confidence_score", None),
                "entities": getattr(extract_result, "extracted_entities", None),
                "has_extracted_review": bool(getattr(extract_result, "extracted_review", None)),
                "clarification_q_count": len(getattr(extract_result, "clarification_questions", []) or [])
            })
            
            # 3. 根据意图路由到不同的处理流程
            if intent_type == "chat":
                # 闲聊模式
                self._trace("Route", {"mode": "chat"})
                response = await self._handle_chat(
                    user_input=user_input,
                    user_profile=user_profile,
                    conversation_history=context.get_history_text(),
                    extract_result=extract_result
                )
            
            elif intent_type == "query":
                # 查询模式
                self._trace("Route", {"mode": "query"})
                response = await self._handle_query(
                    user_input=user_input,
                    user_profile=user_profile,
                    conversation_history=context.get_history_text(),
                    extract_result=extract_result
                )
            
            elif intent_type == "provide_info":
                # 提供信息模式
                self._trace("Route", {"mode": "provide_info"})
                response = await self._handle_info_submission(
                    user_input=user_input,
                    user_profile=user_profile,
                    conversation_history=context.get_history_text(),
                    extract_result=extract_result
                )
            
            else:
                # 未知意图，默认闲聊模式
                logger.warning(f"Unknown intent type: {intent_type}, fallback to chat")
                self._trace("Route", {"mode": "chat_fallback", "unknown_intent": intent_type})
                response = await self._handle_chat(
                    user_input=user_input,
                    user_profile=user_profile,
                    conversation_history=context.get_history_text(),
                    extract_result=extract_result
                )
            
            # 4. 更新对话历史
            assistant_response = response.get("response_text", "")
            context.add_turn(user_input, assistant_response)
            
            # 5. 更新用户画像
            self.profile_manager.update_profile(
                user_id=user_id,
                interaction={
                    "input": user_input,
                    "intent": intent_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # 6. 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()

            self._trace("Output", {
                "intent_type": intent_type,
                "response_preview": self._truncate(assistant_response, 200),
                "execution_time": execution_time
            })

            metadata = response.get("metadata", {}) if isinstance(response, dict) else {}
            
            return {
                "success": True,
                "user_id": user_id,
                "intent_type": intent_type,
                "response_text": assistant_response,
                "extract_result": extract_result.model_dump() if extract_result else None,
                "metadata": metadata,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "additional_info": response.get("additional_info", {})
            }
        
        except Exception as e:
            # 仅在异常时输出简洁信息
            self._trace_print(f"[FRONTEND][ERROR] {type(e).__name__}: {str(e)}")
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": False,
                "user_id": user_id,
                "error_message": str(e),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _extract_intent_and_entities(
        self,
        user_input: str,
        conversation_history: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> InfoExtractResult:
        """
        提取用户意图和实体信息
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            additional_context: 额外上下文
            
        Returns:
            信息提取结果
        """
        context_dict = {
            "user_input": user_input,
            "conversation_history": conversation_history
        }
        
        if additional_context:
            context_dict.update(additional_context)
        
        result = await self.info_extractor.process(context_dict)
        return result
    
    async def _handle_chat(
        self,
        user_input: str,
        user_profile: UserPersonalityVector,
        conversation_history: str,
        extract_result: InfoExtractResult
    ) -> Dict[str, Any]:
        """
        处理闲聊模式
        
        Args:
            user_input: 用户输入
            user_profile: 用户画像
            conversation_history: 对话历史
            extract_result: 信息提取结果
            
        Returns:
            回复字典
        """
        self._trace("Persona.input", {
            "mode": "chat",
            "query_preview": self._truncate(user_input, 160),
            "history_chars": len(conversation_history or "")
        })
        
        # 使用 PersonaAgent 生成个性化回复
        persona_input = {
            "query": user_input,
            "user_profile": user_profile.model_dump(),
            "conversation_history": conversation_history,
            "rag_results": []  # 闲聊模式不使用RAG
        }
        
        persona_response = await self.persona_agent.process(persona_input)

        self._trace("Persona.output", {
            "mode": "chat",
            "response_preview": self._truncate(persona_response.response_text, 200),
            "applied_style": getattr(persona_response, "applied_style", None)
        })
        
        return {
            "response_text": persona_response.response_text,
            "additional_info": {
                "mode": "chat",
                "applied_style": persona_response.applied_style
            },
            "metadata": {
                "persona_strategy": persona_response.applied_style
            }
        }
    
    async def _handle_query(
        self,
        user_input: str,
        user_profile: UserPersonalityVector,
        conversation_history: str,
        extract_result: InfoExtractResult
    ) -> Dict[str, Any]:
        """
        处理查询模式
        
        Args:
            user_input: 用户输入
            user_profile: 用户画像
            conversation_history: 对话历史
            extract_result: 信息提取结果
            
        Returns:
            回复字典
        """
        self._trace("Query.input", {
            "mode": "query",
            "query_preview": self._truncate(user_input, 160),
            "enable_rag": bool(self.enable_rag and self.rag_retriever)
        })
        
        # 1. 后端检索 / RAG检索
        rag_results = []
        backend_query = {
            "called": False,
            "source": None,
            "count": 0
        }
        if self.backend_pipeline and hasattr(self.backend_pipeline, "query_knowledge"):
            try:
                backend_query["called"] = True
                backend_query["source"] = "backend_pipeline"
                rag_results = await self.backend_pipeline.query_knowledge(
                    query=user_input,
                    user_id=user_profile.user_id,
                    limit=5,
                    filters=extract_result.extracted_entities
                )
                backend_query["count"] = len(rag_results)
                self._trace("Backend.query", backend_query)
            except Exception as e:
                self._trace_print(f"[BACKEND][ERROR] query: {type(e).__name__}: {str(e)}")
        elif self.enable_rag and self.rag_retriever:
            try:
                rag_results = await self._retrieve_knowledge(
                    query=user_input,
                    entities=extract_result.extracted_entities
                )
                backend_query["called"] = True
                backend_query["source"] = "rag_retriever"
                backend_query["count"] = len(rag_results)
                self._trace("RAG.query", backend_query)
            except Exception as e:
                self._trace_print(f"[FRONTEND][ERROR] RAG retrieval: {type(e).__name__}: {str(e)}")
        
        # 2. 使用 PersonaAgent 生成回复
        persona_input = {
            "query": user_input,
            "user_profile": user_profile.model_dump(),
            "conversation_history": conversation_history,
            "rag_results": rag_results
        }
        
        persona_response = await self.persona_agent.process(persona_input)

        self._trace("Persona.output", {
            "mode": "query",
            "response_preview": self._truncate(persona_response.response_text, 200),
            "applied_style": getattr(persona_response, "applied_style", None),
            "rag_count": len(rag_results)
        })
        
        return {
            "response_text": persona_response.response_text,
            "additional_info": {
                "mode": "query",
                "applied_style": persona_response.applied_style,
                "rag_count": len(rag_results),
                "extracted_entities": extract_result.extracted_entities
            },
            "metadata": {
                "persona_strategy": persona_response.applied_style,
                "rag_count": len(rag_results),
                "backend_query": backend_query
            }
        }
    
    async def _handle_info_submission(
        self,
        user_input: str,
        user_profile: UserPersonalityVector,
        conversation_history: str,
        extract_result: InfoExtractResult
    ) -> Dict[str, Any]:
        """
        处理信息提交模式（用户提供评价）
        
        Args:
            user_input: 用户输入
            user_profile: 用户画像
            conversation_history: 对话历史
            extract_result: 信息提取结果
            
        Returns:
            回复字典
        """
        self._trace("InfoSubmission.input", {
            "mode": "provide_info",
            "mentor_name": extract_result.extracted_entities.get("mentor_name"),
            "dimension": extract_result.extracted_entities.get("dimension"),
            "has_extracted_review": bool(extract_result.extracted_review)
        })
        
        # 1. 检查是否成功提取了 RawReview
        if not extract_result.extracted_review:
            # 提取失败，需要澄清
            clarification_message = "感谢您的分享！为了更好地记录您的评价，能否提供更多信息？"
            
            if extract_result.clarification_questions:
                clarification_message += "\n\n" + "\n".join(extract_result.clarification_questions)
            
            return {
                "response_text": clarification_message,
                "additional_info": {
                    "mode": "info_submission",
                    "status": "needs_clarification",
                    "extracted_entities": extract_result.extracted_entities
                },
                "metadata": {
                    "backend_processing": {"called": False, "status": "needs_clarification"}
                }
            }
        
        # 2. 将 RawReview 送入后端流水线处理
        processing_result = None
        if self.backend_pipeline:
            try:
                self._trace("Backend.call", {
                    "called": True,
                    "raw_review_preview": self._truncate(extract_result.extracted_review.content, 160)
                })
                processing_result = await self.backend_pipeline.process(extract_result.extracted_review)
                self._trace("Backend.result", {
                    "status": "success",
                    "mentor_id": getattr(processing_result, "mentor_id", None),
                    "dimension": getattr(processing_result, "dimension", None),
                    "weight_score": getattr(processing_result, "weight_score", None)
                })
            except Exception as e:
                self._trace_print(f"[BACKEND][ERROR] {type(e).__name__}: {str(e)}")
                return {
                    "response_text": "抱歉，处理您的信息时出现了问题。请稍后再试。",
                    "additional_info": {
                        "mode": "info_submission",
                        "status": "processing_failed",
                        "error": str(e)
                    },
                    "metadata": {
                        "backend_processing": {"called": True, "status": "failed", "error": str(e)}
                    }
                }
        else:
            logger.warning("Backend pipeline not configured, skipping processing")
        
        # 3. 生成确认回复
        mentor_info = extract_result.extracted_entities.get("mentor_name", "该导师")
        dimension_info = extract_result.extracted_entities.get("dimension", "相关方面")
        
        confirmation_prompt = f"""
        用户提供了以下评价信息：
        - 导师/机构：{mentor_info}
        - 评价维度：{dimension_info}
        - 评价内容：{extract_result.extracted_review.content}
        
        请生成一个友好的确认回复，告知用户我们已收到并处理了他们的评价。
        """
        
        persona_input = {
            "query": confirmation_prompt,
            "user_profile": user_profile.model_dump(),
            "conversation_history": conversation_history,
            "rag_results": []
        }
        
        persona_response = await self.persona_agent.process(persona_input)

        self._trace("Persona.output", {
            "mode": "info_submission",
            "response_preview": self._truncate(persona_response.response_text, 200),
            "applied_style": getattr(persona_response, "applied_style", None)
        })
        
        return {
            "response_text": persona_response.response_text,
            "additional_info": {
                "mode": "info_submission",
                "status": "processed",
                "extracted_review": extract_result.extracted_review.model_dump(),
                "processing_result": processing_result.model_dump() if processing_result else None
            },
            "metadata": {
                "persona_strategy": persona_response.applied_style,
                "backend_processing": {
                    "called": bool(self.backend_pipeline),
                    "status": "success" if processing_result else "skipped"
                }
            }
        }
    
    async def _retrieve_knowledge(
        self,
        query: str,
        entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从知识库检索相关信息
        
        Args:
            query: 查询文本
            entities: 提取的实体信息
            
        Returns:
            检索结果列表
        """
        if not self.rag_retriever:
            return []
        
        # 这里是RAG检索的占位实现
        # 实际使用时应该调用 Mem0 或其他向量检索系统
        try:
            # 示例：调用检索器
            # results = await self.rag_retriever.search(query, top_k=5)
            results = []
            logger.info(f"RAG retrieval completed: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")
            return []
    
    def clear_conversation(self, user_id: str):
        """
        清空指定用户的对话历史
        
        Args:
            user_id: 用户ID
        """
        if user_id in self.conversations:
            self.conversations[user_id].clear()
            logger.info(f"Cleared conversation history for user: {user_id}")
    
    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户对话统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计信息字典
        """
        context = self.get_or_create_context(user_id)
        user_profile = self.profile_manager.get_profile(user_id)
        
        return {
            "user_id": user_id,
            "conversation_turns": len(context.history) // 2,
            "created_at": context.created_at.isoformat(),
            "last_interaction": context.last_interaction.isoformat(),
            "total_interactions": user_profile.interaction_history_count,
            "profile": user_profile.model_dump()
        }
