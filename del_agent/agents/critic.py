"""
Critic Agent - 判别节点智能体
负责评估其他 Agent 的输出质量，是 Verification Loop 的核心组件

版本：2.2.1
更新：支持严格度提示词生成器，动态调整评审标准
"""

from typing import Any, Dict, Optional, Type
import logging
from pydantic import BaseModel

# 处理相对导入问题
try:
    from ..core.base_agent import BaseAgent
    from ..models.schemas import CriticFeedback
    from ..core.prompt_manager import PromptManager
except (ImportError, ValueError):
    # 如果相对导入失败，使用绝对导入
    from core.base_agent import BaseAgent
    from models.schemas import CriticFeedback
    from core.prompt_manager import PromptManager


class CriticAgent(BaseAgent):
    """
    判别节点智能体
    
    功能：
    1. 评估上游 Agent 的输出质量
    2. 判断是否符合预设标准
    3. 提供详细的反馈和改进建议
    4. 支持可调节的严格度等级
    
    工作流程：
    Input: (Agent输出, 原始输入, 严格度) → LLM评估 → CriticFeedback
    
    使用场景：
    - 在 Verification Loop 中作为判别器
    - 质量保证检查
    - 输出标准化验证
    """
    
    def __init__(
        self,
        llm_provider,
        prompt_manager: Optional[PromptManager] = None,
        strictness_level: float = 0.7,
        use_dynamic_prompt: bool = False,
        **kwargs
    ):
        """
        初始化判别节点智能体
        
        Args:
            llm_provider: LLM提供者
            prompt_manager: 提示词管理器（可选）
            strictness_level: 严格度等级，范围 0.0-1.0
                - 0.3-0.5: 宽松（允许较大偏差）
                - 0.6-0.8: 标准（正常质量要求）
                - 0.9-1.0: 严格（要求近乎完美）
            use_dynamic_prompt: 是否使用动态提示词生成器（2.2.1 新增）
            **kwargs: 其他配置参数
        """
        super().__init__(
            name="CriticAgent",
            llm_provider=llm_provider,
            prompt_manager=prompt_manager,
            **kwargs
        )
        
        # 验证严格度参数
        if not 0 <= strictness_level <= 1:
            raise ValueError("strictness_level must be between 0 and 1")
        
        self.strictness_level = strictness_level
        self.use_dynamic_prompt = use_dynamic_prompt
        self.logger = logging.getLogger(f"{__name__}.CriticAgent")
        
        # 定义评估维度权重
        self.evaluation_dimensions = {
            "factual_accuracy": 0.4,      # 事实准确性
            "information_completeness": 0.3,  # 信息完整性
            "format_correctness": 0.2,    # 格式正确性
            "consistency": 0.1            # 一致性
        }
        
        # 初始化严格度提示词生成器（如果启用）
        self.prompt_generator = None
        if use_dynamic_prompt:
            try:
                try:
                    from .strictness_prompt_generator import StrictnessPromptGenerator
                except ImportError:
                    from strictness_prompt_generator import StrictnessPromptGenerator
                
                self.prompt_generator = StrictnessPromptGenerator(
                    llm_provider=llm_provider,
                    prompt_manager=prompt_manager
                )
                self.logger.info("Dynamic prompt generation enabled")
            except Exception as e:
                self.logger.warning(
                    f"Failed to initialize prompt generator: {e}. "
                    "Falling back to static prompts."
                )
                self.use_dynamic_prompt = False
        
        self.logger.info(
            f"CriticAgent initialized with strictness_level={strictness_level}, "
            f"dynamic_prompt={use_dynamic_prompt}"
        )
    
    def get_output_schema(self) -> Type[BaseModel]:
        """获取输出模式"""
        return CriticFeedback
    
    def get_prompt_template_name(self) -> str:
        """获取提示词模板名称"""
        return "critic"
    
    def prepare_input(
        self,
        raw_input: Any,
        agent_output: Optional[BaseModel] = None,
        original_input: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        准备评估输入数据
        
        Args:
            raw_input: 原始输入（如果是字典，可能包含 agent_output 和 original_input）
            agent_output: 待评估的 Agent 输出（可选）
            original_input: 原始输入数据（可选）
            **kwargs: 其他参数
            
        Returns:
            处理后的输入数据字典
        """
        # 如果 raw_input 是字典，尝试从中提取
        if isinstance(raw_input, dict):
            agent_output = raw_input.get('agent_output', agent_output)
            original_input = raw_input.get('original_input', original_input)
            # 如果字典中有 strictness_level，使用它（但不覆盖实例属性）
            strictness = raw_input.get('strictness_level', self.strictness_level)
        else:
            strictness = self.strictness_level
        
        # 转换 agent_output 为字典格式
        if agent_output is not None:
            if isinstance(agent_output, BaseModel):
                agent_output_dict = agent_output.dict()
            elif isinstance(agent_output, dict):
                agent_output_dict = agent_output
            else:
                agent_output_dict = {"content": str(agent_output)}
        else:
            agent_output_dict = {}
        
        # 转换 original_input
        if original_input is not None:
            original_input_str = str(original_input)
        else:
            original_input_str = str(raw_input)
        
        # 构建输入数据
        input_data = {
            "agent_output": agent_output_dict,
            "original_input": original_input_str,
            "strictness_level": strictness,
            "strictness_description": self._get_strictness_description(strictness),
            "evaluation_dimensions": self.evaluation_dimensions,
            **kwargs
        }
        
        self.logger.debug(
            f"Prepared evaluation input: "
            f"strictness={strictness}, "
            f"output_keys={list(agent_output_dict.keys())}"
        )
        
        return input_data
    
    def _get_strictness_description(self, level: float) -> str:
        """
        获取严格度等级的描述
        
        Args:
            level: 严格度等级 (0.0-1.0)
            
        Returns:
            描述字符串
        """
        if level < 0.5:
            return "宽松（允许较大偏差，重点检查基本正确性）"
        elif level < 0.8:
            return "标准（正常质量要求，检查准确性和完整性）"
        else:
            return "严格（要求近乎完美，细致检查所有细节）"
    
    def _generate_dynamic_prompt(self, strictness_level: Optional[float] = None):
        """
        使用严格度提示词生成器生成动态提示词（2.2.1 新增）
        
        Args:
            strictness_level: 严格度级别（可选，默认使用实例的 strictness_level）
        
        Returns:
            生成的提示词结果，如果失败则返回 None
        """
        if not self.use_dynamic_prompt or not self.prompt_generator:
            return None
        
        level = strictness_level if strictness_level is not None else self.strictness_level
        
        try:
            # 获取基础提示词
            if self.prompt_manager:
                base_prompts = self.prompt_manager.get_prompt("critic")
                base_system_prompt = base_prompts.get("system_prompt", "")
                base_user_prompt = base_prompts.get("user_prompt", "")
            else:
                self.logger.warning("No prompt_manager available, using default base prompt")
                base_system_prompt = "你是一个质量评审专家，负责评估 AI Agent 的输出质量。"
                base_user_prompt = ""
            
            # 使用生成器生成新提示词
            result = self.prompt_generator.generate_prompt(
                base_system_prompt=base_system_prompt,
                strictness_level=level,
                base_user_prompt=base_user_prompt
            )
            
            if result.success:
                self.logger.debug(
                    f"Generated dynamic prompt for strictness={level}: "
                    f"{result.key_adjustments}"
                )
                return result
            else:
                self.logger.error(f"Prompt generation failed: {result.error_message}")
                return None
        
        except Exception as e:
            self.logger.error(f"Failed to generate dynamic prompt: {e}")
            return None
    
    def _apply_dynamic_prompt(self, prompt_result, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用动态生成的提示词到输入数据
        
        Args:
            prompt_result: 提示词生成结果
            input_data: 原始输入数据
        
        Returns:
            更新后的输入数据
        """
        if not prompt_result:
            return input_data
        
        # 将生成的提示词添加到输入数据中
        # 这里使用一个特殊键来标记使用动态提示词
        input_data["_dynamic_system_prompt"] = prompt_result.system_prompt
        input_data["_dynamic_user_prompt"] = prompt_result.user_prompt_template
        input_data["_strictness_description"] = prompt_result.strictness_description
        input_data["_prompt_adjustments"] = prompt_result.key_adjustments
        
        return input_data
    
    def set_strictness_level(self, level: float, regenerate_prompt: bool = True):
        """
        动态调整严格度等级（支持提示词重新生成）
        
        Args:
            level: 新的严格度等级 (0.0-1.0)
            regenerate_prompt: 是否重新生成提示词（仅在 use_dynamic_prompt=True 时有效）
        """
        if not 0 <= level <= 1:
            raise ValueError("strictness_level must be between 0 and 1")
        
        old_level = self.strictness_level
        self.strictness_level = level
        
        self.logger.info(f"Strictness level changed: {old_level} -> {level}")
        
        # 如果启用动态提示词且需要重新生成
        if self.use_dynamic_prompt and regenerate_prompt and self.prompt_generator:
            prompt_result = self._generate_dynamic_prompt(level)
            if prompt_result:
                self.logger.info(
                    f"Prompt regenerated for new strictness level. "
                    f"Adjustments: {prompt_result.key_adjustments}"
                )
    
    def validate_output(self, output: CriticFeedback) -> bool:
        """
        验证输出数据
        
        Args:
            output: 判别反馈结果
            
        Returns:
            是否验证通过
        """
        try:
            # 基本字段检查
            if not isinstance(output.is_approved, bool):
                self.logger.error("is_approved must be boolean")
                return False
            
            if not output.reasoning or not output.reasoning.strip():
                self.logger.error("reasoning cannot be empty")
                return False
            
            # 置信度检查
            if not 0 <= output.confidence_score <= 1:
                self.logger.error(
                    f"confidence_score {output.confidence_score} out of range [0, 1]"
                )
                return False
            
            # 如果未通过，应该有建议
            if not output.is_approved and not output.suggestion:
                self.logger.warning(
                    "Output not approved but no suggestion provided"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {str(e)}")
            return False
    
    def evaluate(
        self,
        agent_output: BaseModel,
        original_input: Any,
        **kwargs
    ) -> CriticFeedback:
        """
        评估 Agent 输出质量（便捷方法）
        
        这是一个高级接口，简化了 Verification Loop 中的调用。
        
        Args:
            agent_output: 待评估的 Agent 输出（Pydantic 模型）
            original_input: 原始输入数据
            **kwargs: 其他参数（如 strictness_level）
            
        Returns:
            CriticFeedback 判别反馈
            
        Example:
            critic = CriticAgent(llm_provider, strictness_level=0.7)
            
            # 评估清洗结果
            cleaning_result = cleaner.process("这老板简直是'学术妲己'！")
            feedback = critic.evaluate(
                agent_output=cleaning_result,
                original_input="这老板简直是'学术妲己'！"
            )
            
            if feedback.is_approved:
                print("质量检查通过")
            else:
                print(f"未通过: {feedback.reasoning}")
                print(f"建议: {feedback.suggestion}")
        """
        self.logger.info("Evaluating agent output...")
        
        # 构建评估输入
        evaluation_input = {
            "agent_output": agent_output,
            "original_input": original_input,
            "strictness_level": kwargs.get('strictness_level', self.strictness_level)
        }
        
        # 调用 process 方法
        result = self.process(evaluation_input, **kwargs)
        
        self.logger.info(
            f"Evaluation complete: "
            f"approved={result.is_approved}, "
            f"confidence={result.confidence_score:.2f}"
        )
        
        return result
    
    def get_evaluation_summary(self, feedback: CriticFeedback) -> str:
        """
        获取评估结果的摘要字符串
        
        Args:
            feedback: 判别反馈
            
        Returns:
            易读的摘要字符串
        """
        status = "✅ 通过" if feedback.is_approved else "❌ 未通过"
        confidence = f"{feedback.confidence_score:.0%}"
        
        summary = f"{status} (置信度: {confidence})\n"
        summary += f"原因: {feedback.reasoning}\n"
        
        if feedback.suggestion:
            summary += f"建议: {feedback.suggestion}"
        
        return summary
    
    def batch_evaluate(
        self,
        outputs_with_inputs: list,
        **kwargs
    ) -> list:
        """
        批量评估多个 Agent 输出
        
        Args:
            outputs_with_inputs: 列表，每个元素是 (agent_output, original_input) 元组
            **kwargs: 其他参数
            
        Returns:
            CriticFeedback 列表
        """
        self.logger.info(f"Starting batch evaluation of {len(outputs_with_inputs)} items")
        
        results = []
        for i, (agent_output, original_input) in enumerate(outputs_with_inputs, 1):
            try:
                feedback = self.evaluate(agent_output, original_input, **kwargs)
                results.append(feedback)
                
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(
                        f"Item {i}/{len(outputs_with_inputs)}: "
                        f"{'✅' if feedback.is_approved else '❌'}"
                    )
                    
            except Exception as e:
                self.logger.error(f"Error evaluating item {i}: {str(e)}")
                # 创建一个错误反馈
                error_feedback = CriticFeedback(
                    is_approved=False,
                    reasoning=f"评估过程出错: {str(e)}",
                    suggestion="请检查输入数据格式",
                    confidence_score=0.0
                )
                results.append(error_feedback)
        
        # 统计
        approved_count = sum(1 for r in results if r.is_approved)
        self.logger.info(
            f"Batch evaluation complete: "
            f"{approved_count}/{len(results)} approved "
            f"({approved_count/len(results):.1%})"
        )
        
        return results
    
    def set_strictness_level(self, level: float, regenerate_prompt: bool = True):
        """
        动态调整严格度等级（支持提示词重新生成）
        
        Args:
            level: 新的严格度等级 (0.0-1.0)
            regenerate_prompt: 是否重新生成提示词（仅在 use_dynamic_prompt=True 时有效）
        """
        if not 0 <= level <= 1:
            raise ValueError("strictness_level must be between 0 and 1")
        
        old_level = self.strictness_level
        self.strictness_level = level
        
        self.logger.info(f"Strictness level changed: {old_level} -> {level}")
        
        # 如果启用动态提示词且需要重新生成
        if self.use_dynamic_prompt and regenerate_prompt and self.prompt_generator:
            prompt_result = self._generate_dynamic_prompt(level)
            if prompt_result:
                self.logger.info(
                    f"Prompt regenerated for new strictness level. "
                    f"Adjustments: {prompt_result.key_adjustments}"
                )
