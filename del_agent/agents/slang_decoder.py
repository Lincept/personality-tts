"""
黑话解码智能体 (SlangDecoderAgent)

功能：
1. 识别评论中的网络黑话、行业术语、隐喻表达
2. 解码黑话并翻译为标准表达
3. 维护动态的黑话词典（支持持久化存储）
4. 输出解码后的文本 + 识别到的黑话词典

作者：AI Data Factory
创建日期：2026-01-19
"""

from typing import Any, Dict, Optional, Type, List
import logging
import json
from pathlib import Path
from pydantic import BaseModel

# 处理相对导入问题
try:
    from ..core.base_agent import BaseAgent
    from ..models.schemas import SlangDecodingResult
    from ..core.prompt_manager import PromptManager
    from ..core.dictionary_store import DictionaryStore, create_dictionary_store
except (ImportError, ValueError):
    # 如果相对导入失败，使用绝对导入
    from core.base_agent import BaseAgent
    from models.schemas import SlangDecodingResult
    from core.prompt_manager import PromptManager
    from core.dictionary_store import DictionaryStore, create_dictionary_store


class SlangDecoderAgent(BaseAgent):
    """
    黑话解码智能体
    
    负责识别并翻译评论中的网络黑话、行业术语、隐喻表达等非标准表达，
    将其转换为标准化的表述，同时维护动态更新的黑话词典。
    
    特性：
    - 支持黑话词典的持久化存储和加载
    - 支持多种词典后端（JSON、Mem0）
    - 动态更新黑话词典
    - 保留原文的语义和情感色彩
    - 可批量处理多条评论
    
    Example:
        >>> llm_provider = LLMProvider(...)
        >>> # 使用 JSON 存储
        >>> decoder = SlangDecoderAgent(llm_provider, slang_dict_path="data/slang_dict.json")
        >>> # 或使用 Mem0 存储
        >>> decoder = SlangDecoderAgent(
        ...     llm_provider,
        ...     dictionary_config={
        ...         "backend": "mem0",
        ...         "mem0_config": {...}
        ...     }
        ... )
        >>> result = decoder.process("这个导师是学术妲己，总是画饼")
        >>> print(result.decoded_text)
        "这个导师善于承诺但不兑现，总是做出承诺但不实现"
        >>> print(result.slang_dictionary)
        {"学术妲己": "善于承诺但不兑现的导师", "画饼": "做出承诺但不实现"}
    """
    
    def __init__(
        self,
        llm_provider,
        slang_dict_path: Optional[Path] = None,
        auto_save: bool = True,
        dictionary_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        初始化黑话解码智能体
        
        Args:
            llm_provider: LLM 提供者实例
            slang_dict_path: 黑话词典文件路径（JSON格式，向后兼容）
            auto_save: 是否自动保存新识别的黑话
            dictionary_config: 词典配置字典（可选，优先级高于 slang_dict_path）
                - backend: "json" 或 "mem0"
                - file_path: JSON 文件路径（backend=json）
                - mem0_config: Mem0 配置（backend=mem0）
                - user_id: 用户 ID（backend=mem0）
            **kwargs: 传递给 BaseAgent 的额外参数
        """
        super().__init__(
            name="SlangDecoderAgent",
            llm_provider=llm_provider,
            **kwargs
        )
        
        # 向后兼容：如果提供了 slang_dict_path 但没有 dictionary_config
        if slang_dict_path and not dictionary_config:
            dictionary_config = {
                "backend": "json",
                "file_path": slang_dict_path,
                "auto_save": auto_save
            }
        
        # 创建词典存储实例
        self.dictionary_store: DictionaryStore = create_dictionary_store(
            dictionary_config or {"backend": "json"}
        )
        
        # 获取词典统计
        stats = self.dictionary_store.get_stats()
        
        self.logger.info(
            f"SlangDecoderAgent initialized with {stats['total_terms']} terms "
            f"(backend: {stats['backend']})"
        )
    
    
    def update_dictionary(self, new_terms: Dict[str, str]) -> int:
        """
        动态更新黑话词典
        
        Args:
            new_terms: 新的黑话词典条目 {黑话: 解释}
        
        Returns:
            int: 新增/更新的条目数量
        """
        before_count = self.dictionary_store.get_stats()['total_terms']
        self.dictionary_store.update(new_terms)
        after_count = self.dictionary_store.get_stats()['total_terms']
        
        updated_count = after_count - before_count
        self.logger.info(f"Updated {updated_count} terms in dictionary")
        
        return updated_count
    
    def get_output_schema(self) -> Type[BaseModel]:
        """
        返回输出数据模型
        
        Returns:
            Type[BaseModel]: SlangDecodingResult 模型类
        """
        return SlangDecodingResult
    
    def get_prompt_template_name(self) -> str:
        """
        返回提示词模板名称
        
        Returns:
            str: 模板名称 "slang_decoder"
        """
        return "slang_decoder"
    
    def prepare_input(self, raw_input: Any, **kwargs) -> Dict[str, Any]:
        """
        准备输入数据
        
        Args:
            raw_input: 原始输入文本
            **kwargs: 额外参数
                - existing_dict: 已有的黑话词典（可选）
        
        Returns:
            Dict[str, Any]: 准备好的输入数据
        """
        # 获取已有词典（使用新的 dictionary_store）
        existing_dict = kwargs.get('existing_dict') or self.dictionary_store.get_all()
        
        # 格式化词典为可读字符串
        dict_str = "\n".join([
            f"- {slang}: {meaning}"
            for slang, meaning in existing_dict.items()
        ]) if existing_dict else "（暂无已知黑话）"
        
        return {
            "text": str(raw_input),
            "existing_dictionary": dict_str,
            "dictionary_size": len(existing_dict)
        }
    
    def validate_output(self, output: SlangDecodingResult) -> bool:
        """
        验证输出结果
        
        Args:
            output: SlangDecodingResult 对象
        
        Returns:
            bool: 是否通过验证
        """
        # 基本验证
        if not output.decoded_text or len(output.decoded_text.strip()) == 0:
            self.logger.error("decoded_text cannot be empty")
            return False
        
        if not isinstance(output.slang_dictionary, dict):
            self.logger.error("slang_dictionary must be a dict")
            return False
        
        # 验证置信度范围
        if not (0.0 <= output.confidence_score <= 1.0):
            self.logger.error(
                f"Invalid confidence_score: {output.confidence_score}"
            )
            return False
        
        # 自动更新词典（如果有新识别的黑话）
        if output.slang_dictionary:
            self.update_dictionary(output.slang_dictionary)
        
        return True
    
    def decode_batch(
        self,
        texts: List[str],
        use_verification: bool = False,
        critic_agent = None
    ) -> List[SlangDecodingResult]:
        """
        批量解码黑话
        
        Args:
            texts: 待解码的文本列表
            use_verification: 是否使用核验循环
            critic_agent: CriticAgent 实例（如果 use_verification=True）
        
        Returns:
            List[SlangDecodingResult]: 解码结果列表
        """
        results = []
        
        for text in texts:
            try:
                if use_verification and critic_agent:
                    result = self.process_with_verification(
                        raw_input=text,
                        critic_agent=critic_agent
                    )
                else:
                    result = self.process(text)
                
                results.append(result)
            
            except Exception as e:
                self.logger.error(f"Failed to decode text: {e}")
                results.append(
                    SlangDecodingResult(
                        decoded_text=text,
                        slang_dictionary={},
                        success=False,
                        error_message=str(e)
                    )
                )
        
        return results
    
    def get_dictionary_stats(self) -> Dict[str, Any]:
        """
        获取词典统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = self.dictionary_store.get_stats()
        all_terms = self.dictionary_store.get_all()
        
        return {
            **stats,
            "sample_terms": dict(list(all_terms.items())[:5]) if all_terms else {}
        }
    
    def search_slang(self, keyword: str, limit: int = 10) -> Dict[str, str]:
        """
        搜索黑话词典
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制
        
        Returns:
            Dict[str, str]: 匹配的黑话条目
        """
        return self.dictionary_store.search(keyword, limit=limit)
    
    def clear_dictionary(self) -> bool:
        """
        清空词典
        
        Returns:
            bool: 是否成功
        """
        self.dictionary_store.clear()
        self.logger.warning("Slang dictionary cleared")
        return True
