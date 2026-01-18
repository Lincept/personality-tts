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
except (ImportError, ValueError):
    # 如果相对导入失败，使用绝对导入
    from core.base_agent import BaseAgent
    from models.schemas import SlangDecodingResult
    from core.prompt_manager import PromptManager


class SlangDecoderAgent(BaseAgent):
    """
    黑话解码智能体
    
    负责识别并翻译评论中的网络黑话、行业术语、隐喻表达等非标准表达，
    将其转换为标准化的表述，同时维护动态更新的黑话词典。
    
    特性：
    - 支持黑话词典的持久化存储和加载
    - 动态更新黑话词典
    - 保留原文的语义和情感色彩
    - 可批量处理多条评论
    
    Example:
        >>> llm_provider = LLMProvider(...)
        >>> decoder = SlangDecoderAgent(llm_provider, slang_dict_path="data/slang_dict.json")
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
        **kwargs
    ):
        """
        初始化黑话解码智能体
        
        Args:
            llm_provider: LLM 提供者实例
            slang_dict_path: 黑话词典文件路径（JSON格式）
            auto_save: 是否自动保存新识别的黑话
            **kwargs: 传递给 BaseAgent 的额外参数
        """
        super().__init__(
            name="SlangDecoderAgent",
            llm_provider=llm_provider,
            **kwargs
        )
        
        self.slang_dict_path = slang_dict_path
        self.auto_save = auto_save
        self.slang_dictionary: Dict[str, str] = self._load_slang_dict()
        
        self.logger.info(
            f"SlangDecoderAgent initialized with {len(self.slang_dictionary)} terms"
        )
    
    def _load_slang_dict(self) -> Dict[str, str]:
        """
        从文件加载黑话词典
        
        Returns:
            Dict[str, str]: 黑话词典 {黑话: 标准解释}
        """
        if self.slang_dict_path and self.slang_dict_path.exists():
            try:
                with open(self.slang_dict_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(
                        f"Loaded {len(data)} slang terms from {self.slang_dict_path}"
                    )
                    return data
            except Exception as e:
                self.logger.error(f"Failed to load slang dictionary: {e}")
                return {}
        else:
            self.logger.info("No slang dictionary file provided, starting with empty dict")
            return {}
    
    def _save_slang_dict(self) -> bool:
        """
        保存黑话词典到文件
        
        Returns:
            bool: 是否保存成功
        """
        if not self.slang_dict_path:
            self.logger.warning("No slang_dict_path specified, cannot save")
            return False
        
        try:
            # 确保目录存在
            self.slang_dict_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.slang_dict_path, 'w', encoding='utf-8') as f:
                json.dump(
                    self.slang_dictionary,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            
            self.logger.info(
                f"Saved {len(self.slang_dictionary)} terms to {self.slang_dict_path}"
            )
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save slang dictionary: {e}")
            return False
    
    def update_dictionary(self, new_terms: Dict[str, str]) -> int:
        """
        动态更新黑话词典
        
        Args:
            new_terms: 新的黑话词典条目 {黑话: 解释}
        
        Returns:
            int: 新增/更新的条目数量
        """
        before_count = len(self.slang_dictionary)
        self.slang_dictionary.update(new_terms)
        after_count = len(self.slang_dictionary)
        
        updated_count = after_count - before_count + sum(
            1 for k in new_terms if k in self.slang_dictionary
        )
        
        self.logger.info(f"Updated {updated_count} terms in dictionary")
        
        # 自动保存
        if self.auto_save:
            self._save_slang_dict()
        
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
        # 获取已有词典
        existing_dict = kwargs.get('existing_dict', self.slang_dictionary)
        
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
        if output.slang_dictionary and self.auto_save:
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
        return {
            "total_terms": len(self.slang_dictionary),
            "dictionary_path": str(self.slang_dict_path) if self.slang_dict_path else None,
            "auto_save_enabled": self.auto_save,
            "sample_terms": dict(list(self.slang_dictionary.items())[:5])
        }
    
    def search_slang(self, keyword: str) -> Dict[str, str]:
        """
        搜索黑话词典
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            Dict[str, str]: 匹配的黑话条目
        """
        return {
            slang: meaning
            for slang, meaning in self.slang_dictionary.items()
            if keyword in slang or keyword in meaning
        }
    
    def clear_dictionary(self) -> bool:
        """
        清空词典
        
        Returns:
            bool: 是否成功
        """
        self.slang_dictionary.clear()
        self.logger.warning("Slang dictionary cleared")
        
        if self.auto_save:
            return self._save_slang_dict()
        
        return True
