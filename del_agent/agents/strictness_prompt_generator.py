"""
严格度提示词生成器 (Strictness Prompt Generator)

功能：
1. 根据严格度参数（0.0-1.0）动态生成/调整 Critic 的提示词
2. 作为 model-based agent，专注于提示词工程
3. 为 CriticAgent 提供更灵活的严格度控制

作者：AI Data Factory
创建日期：2026-01-19
版本：2.2.1
"""

from typing import Any, Dict, Optional, Type
import logging
from pydantic import BaseModel, Field

# 处理相对导入问题
try:
    from ..core.base_agent import BaseAgent
    from ..core.prompt_manager import PromptManager
except (ImportError, ValueError):
    from core.base_agent import BaseAgent
    from core.prompt_manager import PromptManager


class PromptGenerationResult(BaseModel):
    """提示词生成结果"""
    
    system_prompt: str = Field(
        description="生成的系统提示词"
    )
    user_prompt_template: str = Field(
        description="生成的用户提示词模板"
    )
    strictness_description: str = Field(
        description="严格度描述"
    )
    key_adjustments: list[str] = Field(
        default_factory=list,
        description="关键调整点说明"
    )
    success: bool = Field(
        default=True,
        description="是否成功生成"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="错误信息"
    )


class StrictnessPromptGenerator(BaseAgent):
    """
    严格度提示词生成器
    
    职责：
    1. 接收基础提示词和严格度参数
    2. 基于严格度动态调整提示词内容
    3. 输出适配后的提示词
    
    严格度分级（0.0-1.0）：
    - 0.0-0.3: 极度宽松 - 只检查基本正确性，容忍大量偏差
    - 0.4-0.6: 宽松 - 允许一定偏差，重点检查核心要素
    - 0.7-0.8: 标准 - 正常质量要求，检查准确性和完整性
    - 0.9-0.95: 严格 - 要求高质量，细致检查所有维度
    - 0.96-1.0: 极度严格 - 近乎完美，不容许任何瑕疵
    
    提示词调整原则：
    1. **评分标准**: 严格度越高，通过阈值越高
    2. **检查维度**: 严格度越高，检查维度越多越细
    3. **反馈详细度**: 严格度越高，反馈越详细具体
    4. **容错能力**: 严格度越低，容错能力越强
    
    Example:
        >>> llm_provider = LLMProvider(...)
        >>> generator = StrictnessPromptGenerator(llm_provider)
        >>> result = generator.generate_prompt(
        ...     base_system_prompt="你是质量评审专家...",
        ...     strictness_level=0.9
        ... )
        >>> print(result.system_prompt)
    """
    
    def __init__(
        self,
        llm_provider,
        prompt_manager: Optional[PromptManager] = None,
        **kwargs
    ):
        """
        初始化严格度提示词生成器
        
        Args:
            llm_provider: LLM 提供者实例
            prompt_manager: 提示词管理器（可选）
            **kwargs: 传递给 BaseAgent 的额外参数
        """
        super().__init__(
            name="StrictnessPromptGenerator",
            llm_provider=llm_provider,
            prompt_manager=prompt_manager,
            **kwargs
        )
        
        self.logger = logging.getLogger(f"{__name__}.StrictnessPromptGenerator")
        self.logger.info("StrictnessPromptGenerator initialized")
    
    def get_output_schema(self) -> Type[BaseModel]:
        """获取输出模式"""
        return PromptGenerationResult
    
    def get_prompt_template_name(self) -> str:
        """获取提示词模板名称"""
        return "strictness_prompt_generator"
    
    def prepare_input(self, raw_input: Any, **kwargs) -> Dict[str, Any]:
        """
        准备输入数据
        
        Args:
            raw_input: 原始输入（可以是字典或其他类型）
            **kwargs: 额外参数
                - base_system_prompt: 基础系统提示词
                - base_user_prompt: 基础用户提示词（可选）
                - strictness_level: 严格度参数（0.0-1.0）
        
        Returns:
            Dict[str, Any]: 准备好的输入数据
        """
        # 如果 raw_input 是字典，尝试从中提取
        if isinstance(raw_input, dict):
            base_system_prompt = raw_input.get('base_system_prompt', '')
            base_user_prompt = raw_input.get('base_user_prompt', '')
            strictness_level = raw_input.get('strictness_level', 0.7)
        else:
            base_system_prompt = kwargs.get('base_system_prompt', '')
            base_user_prompt = kwargs.get('base_user_prompt', '')
            strictness_level = kwargs.get('strictness_level', 0.7)
        
        # 验证严格度参数
        if not 0 <= strictness_level <= 1:
            self.logger.warning(f"Invalid strictness_level {strictness_level}, using 0.7")
            strictness_level = 0.7
        
        # 生成严格度描述和分级信息
        strictness_info = self._get_strictness_info(strictness_level)
        
        input_data = {
            "base_system_prompt": base_system_prompt,
            "base_user_prompt": base_user_prompt,
            "strictness_level": strictness_level,
            "strictness_category": strictness_info["category"],
            "strictness_description": strictness_info["description"],
            "pass_threshold": strictness_info["pass_threshold"],
            "key_focus": strictness_info["key_focus"],
            "tolerance": strictness_info["tolerance"],
            **kwargs
        }
        
        self.logger.debug(
            f"Prepared input for strictness={strictness_level} "
            f"({strictness_info['category']})"
        )
        
        return input_data
    
    def _get_strictness_info(self, strictness_level: float) -> Dict[str, Any]:
        """
        根据严格度生成详细信息
        
        Args:
            strictness_level: 严格度参数（0.0-1.0）
        
        Returns:
            Dict: 严格度详细信息
        """
        if strictness_level <= 0.3:
            return {
                "category": "极度宽松",
                "description": "只检查基本正确性，容忍大量偏差和不完整",
                "pass_threshold": 40,  # 40分即可通过
                "key_focus": ["基本事实正确性"],
                "tolerance": "高度容忍格式问题、信息缺失、表达不准确"
            }
        elif strictness_level <= 0.6:
            return {
                "category": "宽松",
                "description": "允许一定偏差，重点检查核心要素完整性",
                "pass_threshold": 60,  # 60分通过
                "key_focus": ["核心信息完整", "基本格式正确"],
                "tolerance": "容忍次要细节缺失、格式略有偏差"
            }
        elif strictness_level <= 0.8:
            return {
                "category": "标准",
                "description": "正常质量要求，检查准确性和完整性",
                "pass_threshold": 75,  # 75分通过
                "key_focus": ["信息准确性", "内容完整性", "格式规范性"],
                "tolerance": "容忍轻微表达差异，不容忍明显错误"
            }
        elif strictness_level <= 0.95:
            return {
                "category": "严格",
                "description": "要求高质量输出，细致检查所有维度",
                "pass_threshold": 85,  # 85分通过
                "key_focus": ["事实准确性", "信息完整性", "格式正确性", "一致性", "表达质量"],
                "tolerance": "不容忍任何明显错误或信息缺失"
            }
        else:  # > 0.95
            return {
                "category": "极度严格",
                "description": "要求近乎完美，不容许任何瑕疵",
                "pass_threshold": 95,  # 95分通过
                "key_focus": [
                    "事实准确性（100%）",
                    "信息完整性（100%）",
                    "格式完美性",
                    "一致性",
                    "表达精准性",
                    "细节完美性"
                ],
                "tolerance": "零容忍任何错误、缺失或不完美"
            }
    
    def generate_prompt(
        self,
        base_system_prompt: str,
        strictness_level: float,
        base_user_prompt: Optional[str] = None
    ) -> PromptGenerationResult:
        """
        生成适配严格度的提示词
        
        这是一个便捷方法，直接调用 process() 并返回结果。
        
        Args:
            base_system_prompt: 基础系统提示词
            strictness_level: 严格度参数（0.0-1.0）
            base_user_prompt: 基础用户提示词（可选）
        
        Returns:
            PromptGenerationResult: 生成的提示词结果
        """
        input_data = {
            "base_system_prompt": base_system_prompt,
            "base_user_prompt": base_user_prompt or "",
            "strictness_level": strictness_level
        }
        
        return self.process(input_data)
    
    def validate_output(self, output: BaseModel) -> bool:
        """
        验证输出结果
        
        Args:
            output: 输出结果
        
        Returns:
            bool: 是否有效
        """
        if not isinstance(output, PromptGenerationResult):
            return False
        
        # 检查必要字段
        if not output.system_prompt or not output.strictness_description:
            self.logger.error("Missing required fields in output")
            return False
        
        # 检查提示词长度
        if len(output.system_prompt) < 50:
            self.logger.warning("Generated system prompt seems too short")
        
        return True
