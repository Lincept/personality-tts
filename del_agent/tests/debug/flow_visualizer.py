#!/usr/bin/env python3
"""
数据流程可视化器
提供可扩展的流程图展示，自动处理中英文字符对齐问题
"""

import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BoxContent:
    """盒子内容数据类"""
    title: str
    items: List[Tuple[str, str]]  # [(label, value), ...]
    icon: str = "🔹"


class FlowVisualizer:
    """
    流程可视化器
    
    功能：
    - 自动处理中英文字符混合对齐
    - 支持动态宽度调整
    - 可扩展的盒子样式
    """
    
    def __init__(self, box_width: int = 72, enable_unicode_width: bool = True):
        """
        初始化可视化器
        
        Args:
            box_width: 盒子宽度（字符数）
            enable_unicode_width: 是否启用Unicode宽度计算（处理中文对齐）
        """
        self.box_width = box_width
        self.enable_unicode_width = enable_unicode_width
        
    def get_display_width(self, text: str) -> int:
        """
        计算文本的显示宽度
        
        中文字符占2个位置，英文字符占1个位置
        
        Args:
            text: 输入文本
            
        Returns:
            显示宽度
        """
        if not self.enable_unicode_width:
            return len(text)
        
        width = 0
        for char in text:
            # East Asian Width: 'F'(全角), 'W'(宽字符) 占2个位置
            # 其他占1个位置
            if unicodedata.east_asian_width(char) in ('F', 'W'):
                width += 2
            else:
                width += 1
        return width
    
    def pad_text(self, text: str, target_width: int, align: str = 'left') -> str:
        """
        填充文本到指定宽度（考虑中文字符宽度）
        
        Args:
            text: 输入文本
            target_width: 目标显示宽度
            align: 对齐方式 ('left', 'right', 'center')
            
        Returns:
            填充后的文本
        """
        current_width = self.get_display_width(text)
        padding_needed = target_width - current_width
        
        if padding_needed <= 0:
            return text
        
        if align == 'left':
            return text + ' ' * padding_needed
        elif align == 'right':
            return ' ' * padding_needed + text
        elif align == 'center':
            left_pad = padding_needed // 2
            right_pad = padding_needed - left_pad
            return ' ' * left_pad + text + ' ' * right_pad
        else:
            return text
    
    def truncate_text(self, text: str, max_width: int, ellipsis: str = "...") -> str:
        """
        截断文本到指定宽度（考虑中文字符宽度）
        
        Args:
            text: 输入文本
            max_width: 最大显示宽度
            ellipsis: 省略号
            
        Returns:
            截断后的文本
        """
        if self.get_display_width(text) <= max_width:
            return text
        
        # 逐字符累加，直到超过宽度
        current_width = 0
        result = []
        ellipsis_width = self.get_display_width(ellipsis)
        
        for char in text:
            char_width = 2 if unicodedata.east_asian_width(char) in ('F', 'W') else 1
            if current_width + char_width + ellipsis_width > max_width:
                break
            result.append(char)
            current_width += char_width
        
        return ''.join(result) + ellipsis
    
    def draw_header_box(self, title: str, content: str) -> List[str]:
        """
        绘制标题盒子（使用双线框）
        
        Args:
            title: 标题
            content: 内容
            
        Returns:
            盒子行列表
        """
        lines = []
        inner_width = self.box_width - 4  # 减去边框和padding
        
        # 上边框
        lines.append("┏" + "━" * (self.box_width - 2) + "┓")
        
        # 标题行
        padded_title = self.pad_text(f"  {title}", inner_width + 2, 'left')
        lines.append("┃" + padded_title + "┃")
        
        # 内容行
        truncated_content = self.truncate_text(content, inner_width - 5)
        padded_content = self.pad_text(f"  📝 {truncated_content}", inner_width + 2, 'left')
        lines.append("┃" + padded_content + "┃")
        
        # 下边框
        lines.append("┗" + "━" * (self.box_width - 2) + "┛")
        
        return lines
    
    def draw_box(self, content: BoxContent) -> List[str]:
        """
        绘制普通盒子（使用单线框）
        
        Args:
            content: 盒子内容
            
        Returns:
            盒子行列表
        """
        lines = []
        inner_width = self.box_width - 4  # 减去边框和padding
        
        # 上边框
        lines.append("┌" + "─" * (self.box_width - 2) + "┐")
        
        # 标题行
        title_text = f"│ {content.icon} {content.title}"
        padded_title = self.pad_text(title_text, self.box_width - 1, 'left')
        lines.append(padded_title + "│")
        
        # 分隔线
        lines.append("├" + "─" * (self.box_width - 2) + "┤")
        
        # 内容行
        for label, value in content.items:
            item_text = f"│   {label}: {value}"
            padded_item = self.pad_text(item_text, self.box_width - 1, 'left')
            lines.append(padded_item + "│")
        
        # 下边框
        lines.append("└" + "─" * (self.box_width - 2) + "┘")
        
        return lines
    
    def draw_footer_box(self, title: str, items: List[Tuple[str, str]]) -> List[str]:
        """
        绘制底部盒子（使用双线框）
        
        Args:
            title: 标题
            items: 内容项列表 [(icon_label, value), ...]
            
        Returns:
            盒子行列表
        """
        lines = []
        inner_width = self.box_width - 4
        
        # 上边框
        lines.append("┏" + "━" * (self.box_width - 2) + "┓")
        
        # 标题行
        padded_title = self.pad_text(f"  {title}", inner_width + 2, 'left')
        lines.append("┃" + padded_title + "┃")
        
        # 内容行
        for icon_label, value in items:
            truncated_value = self.truncate_text(value, inner_width - len(icon_label) - 5)
            item_text = f"  {icon_label} {truncated_value}"
            padded_item = self.pad_text(item_text, inner_width + 2, 'left')
            lines.append("┃" + padded_item + "┃")
        
        # 下边框
        lines.append("┗" + "━" * (self.box_width - 2) + "┛")
        
        return lines
    
    def draw_arrow(self, width: Optional[int] = None) -> str:
        """
        绘制箭头连接线
        
        Args:
            width: 箭头左侧空格数，默认居中
            
        Returns:
            箭头行
        """
        if width is None:
            width = (self.box_width - 1) // 2
        return " " * width + "↓"
    
    def draw_flow(
        self, 
        input_text: str,
        boxes: List[BoxContent],
        output_items: List[Tuple[str, str]],
        input_title: str = "原始输入",
        output_title: str = "✅ 结构化知识节点（最终输出）"
    ) -> List[str]:
        """
        绘制完整的数据流程图
        
        Args:
            input_text: 输入文本
            boxes: 中间处理盒子列表
            output_items: 输出项列表
            input_title: 输入标题
            output_title: 输出标题
            
        Returns:
            完整流程图行列表
        """
        lines = []
        
        # 输入盒子
        lines.extend(self.draw_header_box(input_title, input_text))
        lines.append(self.draw_arrow())
        
        # 中间处理盒子
        for box in boxes:
            lines.extend(self.draw_box(box))
            lines.append(self.draw_arrow())
        
        # 输出盒子
        lines.extend(self.draw_footer_box(output_title, output_items))
        
        return lines


def create_backend_flow(
    raw_content: str,
    agent_outputs: Dict[str, Any],
    box_width: int = 72
) -> List[str]:
    """
    创建后端数据工厂流程图
    
    Args:
        raw_content: 原始评价内容
        agent_outputs: Agent输出字典
        box_width: 盒子宽度
        
    Returns:
        流程图行列表
    """
    visualizer = FlowVisualizer(box_width=box_width)
    
    # 准备盒子内容
    boxes = []
    
    # 1. RawCommentCleaner
    cleaner_output = agent_outputs.get('cleaner')
    if cleaner_output:
        factual = visualizer.truncate_text(cleaner_output.factual_content, 50)
        boxes.append(BoxContent(
            title="Agent 1: RawCommentCleaner (清洗)",
            items=[
                ("输出内容", factual),
                ("情绪强度", str(cleaner_output.emotional_intensity)),
                ("关键词数", str(len(cleaner_output.keywords)))
            ]
        ))
    
    # 2. SlangDecoderAgent
    decoder_output = agent_outputs.get('decoder')
    if decoder_output:
        decoded = visualizer.truncate_text(decoder_output.decoded_text, 50)
        boxes.append(BoxContent(
            title="Agent 2: SlangDecoderAgent (黑话解码)",
            items=[
                ("解码内容", decoded),
                ("识别黑话", str(len(decoder_output.slang_dictionary))),
                ("置信度", str(decoder_output.confidence_score))
            ]
        ))
    
    # 3. WeigherAgent
    weigher_output = agent_outputs.get('weigher')
    if weigher_output:
        boxes.append(BoxContent(
            title="Agent 3: WeigherAgent (权重分析)",
            items=[
                ("最终权重", f"{weigher_output.weight_score:.3f}"),
                ("身份可信", f"{weigher_output.identity_confidence:.3f}"),
                ("时间衰减", f"{weigher_output.time_decay:.3f}")
            ]
        ))
    
    # 4. CompressorAgent
    compressor_output = agent_outputs.get('compressor')
    if compressor_output:
        node = compressor_output.structured_node
        fact = visualizer.truncate_text(node.fact_content, 50)
        boxes.append(BoxContent(
            title="Agent 4: CompressorAgent (结构化压缩)",
            items=[
                ("维度分类", node.dimension),
                ("事实内容", fact),
                ("标签数量", str(len(node.tags)))
            ]
        ))
    
    # 准备输出项
    output_items = []
    if compressor_output:
        node = compressor_output.structured_node
        output_items = [
            ("📦", node.fact_content),
            ("🏷️  维度:", node.dimension),
            ("⚖️  权重:", str(node.weight_score))
        ]
    
    # 绘制流程图
    return visualizer.draw_flow(
        input_text=raw_content,
        boxes=boxes,
        output_items=output_items
    )


def create_frontend_flow(
    user_input: str,
    extract_result: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]] = None,
    box_width: int = 72
) -> List[str]:
    """
    创建前端处理流程图
    
    Args:
        user_input: 用户输入
        extract_result: InfoExtractorAgent的提取结果
        user_profile: 用户画像信息（可选）
        box_width: 盒子宽度
        
    Returns:
        流程图行列表
    """
    visualizer = FlowVisualizer(box_width=box_width)
    lines = []
    
    def truncate(text, max_len=50):
        return visualizer.truncate_text(text, max_len)
    
    intent = extract_result.get('intent_type', 'unknown')
    entities = extract_result.get('extracted_entities', {})
    confidence = extract_result.get('confidence_score', 0)
    
    lines.append("")
    lines.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    lines.append("┃  👤 用户输入                                                           ┃")
    padded_input = visualizer.pad_text(f"  💬 {truncate(user_input, 60)}", 68, 'left')
    lines.append(f"┃{padded_input} ┃")
    lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    lines.append("                                 ↓")
    
    # InfoExtractorAgent
    lines.append("┌────────────────────────────────────────────────────────────────────────┐")
    lines.append("│ 🎯 Agent: InfoExtractorAgent (意图识别)                               │")
    lines.append("├────────────────────────────────────────────────────────────────────────┤")
    intent_line = visualizer.pad_text(f"   检测意图: {intent}", 70, 'left')
    lines.append(f"│{intent_line} │")
    conf_line = visualizer.pad_text(f"   置信度: {confidence}", 70, 'left')
    lines.append(f"│{conf_line} │")
    
    if entities.get('mentor_name'):
        mentor_line = visualizer.pad_text(f"   导师名: {entities.get('mentor_name', 'N/A')}", 70, 'left')
        lines.append(f"│{mentor_line} │")
    if entities.get('dimension'):
        dims = ', '.join(entities.get('dimension', [])[:3])
        dim_line = visualizer.pad_text(f"   相关维度: {truncate(dims, 55)}", 70, 'left')
        lines.append(f"│{dim_line} │")
    
    lines.append("└────────────────────────────────────────────────────────────────────────┘")
    lines.append("                                 ↓")
    
    # UserProfileManager
    if user_profile:
        lines.append("┌────────────────────────────────────────────────────────────────────────┐")
        lines.append("│ 👥 UserProfileManager (用户画像)                                      │")
        lines.append("├────────────────────────────────────────────────────────────────────────┤")
        vector = user_profile.get('personality_vector', {})
        vector_line = f"   幽默度: {vector.get('humor', 0.5):.2f}  正式度: {vector.get('formality', 0.5):.2f}  简洁度: {vector.get('detail', 0.5):.2f}"
        padded_vector = visualizer.pad_text(vector_line, 70, 'left')
        lines.append(f"│{padded_vector} │")
        count_line = visualizer.pad_text(f"   交互次数: {user_profile.get('interaction_count', 0)}", 70, 'left')
        lines.append(f"│{count_line} │")
        lines.append("└────────────────────────────────────────────────────────────────────────┘")
        lines.append("                                 ↓")
    
    lines.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    lines.append("┃  ✅ 前端处理完成，准备生成响应                                         ┃")
    lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    lines.append("")
    
    return lines


def create_full_interaction_flow(
    user_input: str,
    result: Dict[str, Any],
    box_width: int = 72
) -> List[str]:
    """
    创建完整的前后端交互流程图
    
    Args:
        user_input: 用户输入
        result: 前端编排器的处理结果
        box_width: 盒子宽度
        
    Returns:
        流程图行列表
    """
    visualizer = FlowVisualizer(box_width=box_width)
    lines = []
    
    def truncate(text, max_len=50):
        return visualizer.truncate_text(text, max_len)
    
    intent = result.get('intent', 'unknown')
    response = result.get('response_text', '')
    metadata = result.get('metadata', {})
    
    lines.append("")
    lines.append("╔════════════════════════════════════════════════════════════════════════╗")
    lines.append("║  🌐 完整交互流程：用户 → 前端 → 后端 → 前端 → 用户                    ║")
    lines.append("╚════════════════════════════════════════════════════════════════════════╝")
    lines.append("")
    
    # 用户输入
    lines.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    lines.append("┃  👤 用户输入                                                           ┃")
    padded_input = visualizer.pad_text(f"  💬 {truncate(user_input, 60)}", 68, 'left')
    lines.append(f"┃{padded_input} ┃")
    lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    lines.append("                                 ↓")
    
    # 前端接收
    lines.append("┌────────────────────────────────────────────────────────────────────────┐")
    lines.append("│ 🎯 前端：Orchestrator (编排器)                                         │")
    lines.append("├────────────────────────────────────────────────────────────────────────┤")
    intent_line = visualizer.pad_text(f"   ① 意图识别: {intent}", 70, 'left')
    lines.append(f"│{intent_line} │")
    
    backend_called = metadata.get('backend_processing', {}).get('called', False)
    route_text = "调用后端" if backend_called else "直接响应"
    route_line = visualizer.pad_text(f"   ② 路由决策: {route_text}", 70, 'left')
    lines.append(f"│{route_line} │")
    lines.append("└────────────────────────────────────────────────────────────────────────┘")
    lines.append("                                 ↓")
    
    # 如果有后端处理
    if backend_called:
        backend_info = metadata['backend_processing']
        
        lines.append("┌────────────────────────────────────────────────────────────────────────┐")
        lines.append("│ 🔧 后端：DataFactory Pipeline (数据工厂)                              │")
        lines.append("├────────────────────────────────────────────────────────────────────────┤")
        lines.append("│   ① RawCommentCleaner → 清洗评价                                      │")
        lines.append("│   ② SlangDecoderAgent → 黑话解码                                      │")
        lines.append("│   ③ WeigherAgent → 计算权重                                           │")
        lines.append("│   ④ CompressorAgent → 结构化压缩                                      │")
        status_line = visualizer.pad_text(f"   状态: {backend_info.get('status', 'unknown')}", 70, 'left')
        lines.append(f"│{status_line} │")
        lines.append("└────────────────────────────────────────────────────────────────────────┘")
        lines.append("                                 ↓")
    
    # 前端响应生成
    lines.append("┌────────────────────────────────────────────────────────────────────────┐")
    lines.append("│ 🎭 前端：PersonaAgent (人格化响应)                                     │")
    lines.append("├────────────────────────────────────────────────────────────────────────┤")
    lines.append("│   根据用户画像生成个性化回复                                           │")
    strategy_line = visualizer.pad_text(f"   响应策略: {metadata.get('persona_strategy', 'default')}", 70, 'left')
    lines.append(f"│{strategy_line} │")
    lines.append("└────────────────────────────────────────────────────────────────────────┘")
    lines.append("                                 ↓")
    
    # 最终输出
    lines.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    lines.append("┃  ✅ 系统响应（返回给用户）                                             ┃")
    response_lines = response.split('\n')
    for line in response_lines[:3]:  # 只显示前3行
        padded_resp = visualizer.pad_text(f"  💬 {truncate(line, 60)}", 68, 'left')
        lines.append(f"┃{padded_resp} ┃")
    if len(response_lines) > 3:
        extra_line = visualizer.pad_text(f"     ...（共{len(response_lines)}行）", 68, 'left')
        lines.append(f"┃{extra_line} ┃")
    lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    lines.append("")
    
    return lines


# ============ 使用示例 ============

if __name__ == "__main__":
    # 简单测试
    visualizer = FlowVisualizer(box_width=72)
    
    # 测试中英文混合对齐
    test_texts = [
        "Hello World",
        "你好世界",
        "混合Mixed文本Text",
        "这是一个很长很长的中文文本，需要被截断处理，看看效果如何"
    ]
    
    print("=== 宽度计算测试 ===")
    for text in test_texts:
        width = visualizer.get_display_width(text)
        print(f"文本: {text}")
        print(f"  实际长度: {len(text)}, 显示宽度: {width}")
        print(f"  填充后: |{visualizer.pad_text(text, 40)}|")
        print()
    
    print("\n=== 流程图测试 ===")
    
    # 创建测试盒子
    box1 = BoxContent(
        title="Agent 1: TestAgent (测试)",
        items=[
            ("输入内容", "测试中文English混合对齐"),
            ("处理结果", "Success成功"),
            ("耗时", "1.23s")
        ]
    )
    
    # 绘制流程
    lines = visualizer.draw_flow(
        input_text="这是一个测试输入，包含中文和English字符",
        boxes=[box1],
        output_items=[
            ("📦", "处理完成的最终结果"),
            ("🏷️  类型:", "测试类型"),
            ("⚖️  分数:", "0.95")
        ]
    )
    
    for line in lines:
        print(line)
