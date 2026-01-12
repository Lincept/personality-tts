"""
语音助手 Prompt 管理系统
包括角色设定、用户信息、知识库、对话历史管理
"""
from typing import List, Dict, Optional
from datetime import datetime


class VoiceAssistantPrompt:
    """语音助手 Prompt 管理器"""

    def __init__(self, role: str = "default", role_config: Optional[Dict] = None, mem0_manager=None):
        """
        初始化 Prompt 管理器

        Args:
            role: 角色类型 (default/casual/professional/companion)
            role_config: 自定义角色配置（从 role_loader 加载）
            mem0_manager: Mem0 记忆管理器（可选）
        """
        self.role = role
        self.custom_role_config = role_config  # 保存自定义角色配置
        self.mem0_manager = mem0_manager  # Mem0 记忆管理器
        self.system_prompt = self._build_system_prompt()
        self.user_info = {}
        self.knowledge_base = []
        self.conversation_history = []
        self.max_history = 10  # 保留最近 10 轮对话

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        # 优先使用自定义角色配置
        if self.custom_role_config:
            role_config = {
                'name': self.custom_role_config['name'],
                'personality': self.custom_role_config['personality'],
                'style': self.custom_role_config['style']
            }
            custom_prompt = self.custom_role_config.get('custom_prompt')
        else:
            # 使用内置角色配置
            role_config = VoiceAssistantConfig.ROLES.get(self.role, VoiceAssistantConfig.ROLES["default"])
            custom_prompt = None

        # 如果有自定义 prompt，使用自定义的
        if custom_prompt:
            base_prompt = custom_prompt + """

【核心规则 - 必须严格遵守】

1. 输出格式要求
   - 简洁回答：每次回答控制在 2-3 句话以内（最多 50 字）
   - 口语化表达：使用自然的口语，就像和朋友聊天一样
   - 绝对禁止使用：
     * Markdown 格式（粗体、标题、代码块等）
     * 特殊符号（*、#、-、_、```、【】、「」等）
     * 列表格式（带序号或符号的列表）
     * 表情符号（除非用户明确要求）
     * 长篇大论或分点列举

2. 对话风格
   - 像朋友一样自然交流
   - 语气亲切、温暖
   - 回答简短有力
   - 避免过于正式或机械

3. 回答策略
   - 优先给出核心答案
   - 如果话题复杂，先给简要回答，然后询问是否需要详细说明
   - 不要一次性输出大量信息
   - 保持对话的互动性

【当前时间】
{{current_time}}

【用户信息】
{{user_info}}

【知识库】
{{knowledge_base}}

记住：你是在和用户语音对话，保持自然、简洁、友好！每次回答不超过 50 字！"""
        else:
            # 使用普通字符串而不是 f-string，保留占位符
            base_prompt = """你是一个{personality}的语音助手。你的回答会通过语音合成（TTS）播放给用户，所以必须适合语音表达。

【角色定位】
- 名称：{name}
- 风格：{style}
- 特点：{personality}

【核心规则 - 必须严格遵守】

1. 输出格式要求
   - 简洁回答：每次回答控制在 2-3 句话以内（最多 50 字）
   - 口语化表达：使用自然的口语，就像和朋友聊天一样
   - 绝对禁止使用：
     * Markdown 格式（粗体、标题、代码块等）
     * 特殊符号（*、#、-、_、```、【】、「」等）
     * 列表格式（带序号或符号的列表）
     * 表情符号（除非用户明确要求）
     * 长篇大论或分点列举

2. 对话风格
   - 像朋友一样自然交流
   - 语气亲切、温暖
   - 回答简短有力
   - 避免过于正式或机械

3. 回答策略
   - 优先给出核心答案
   - 如果话题复杂，先给简要回答，然后询问是否需要详细说明
   - 不要一次性输出大量信息
   - 保持对话的互动性

【示例对话】

错误示例 1：
用户：推荐攀岩鞋
助手：当然！以下是几个推荐：1. La Sportiva - 特点：专业性强，推荐型号：Tarantulace 适合初学者，Miura 适合进阶。2. Scarpa...

正确示例 1：
用户：推荐攀岩鞋
助手：我推荐 La Sportiva 的 Tarantulace，特别适合初学者，舒适又不贵。你是刚开始玩攀岩吗？

错误示例 2：
用户：今天天气怎么样
助手：根据气象数据显示，今天的天气情况如下：温度 15 到 22 摄氏度，湿度 60%，风力 3 到 4 级。建议您...

正确示例 2：
用户：今天天气怎么样
助手：今天挺舒服的，15 到 22 度，适合出门。你要出去玩吗？

错误示例 3：
用户：介绍一下 Python
助手：Python 是一种高级编程语言，具有以下特点：1）语法简洁 2）功能强大 3）应用广泛...

正确示例 3：
用户：介绍一下 Python
助手：Python 是一种很好学的编程语言，语法简单，用途广泛。你想学编程吗？

【当前时间】
{{current_time}}

【用户信息】
{{user_info}}

【知识库】
{{knowledge_base}}

记住：你是在和用户语音对话，保持自然、简洁、友好！每次回答不超过 50 字！"""

            # 先格式化角色信息
            base_prompt = base_prompt.format(
                name=role_config['name'],
                style=role_config['style'],
                personality=role_config['personality']
            )

        return base_prompt

    def set_role(self, role: str):
        """
        切换助手角色

        Args:
            role: 角色类型 (default/casual/professional/companion)
        """
        if role not in VoiceAssistantConfig.ROLES:
            raise ValueError(f"未知角色: {role}，可选: {list(VoiceAssistantConfig.ROLES.keys())}")

        self.role = role
        self.system_prompt = self._build_system_prompt()

    def get_role_info(self) -> Dict:
        """获取当前角色信息"""
        return VoiceAssistantConfig.ROLES.get(self.role, VoiceAssistantConfig.ROLES["default"])

    def set_user_info(self, name: Optional[str] = None,
                     preferences: Optional[Dict] = None,
                     context: Optional[Dict] = None):
        """
        设置用户信息

        Args:
            name: 用户名称
            preferences: 用户偏好
            context: 上下文信息
        """
        if name:
            self.user_info['name'] = name
        if preferences:
            self.user_info['preferences'] = preferences
        if context:
            self.user_info['context'] = context

    def add_knowledge(self, knowledge: str, category: Optional[str] = None):
        """
        添加知识库条目

        Args:
            knowledge: 知识内容
            category: 知识分类
        """
        self.knowledge_base.append({
            'content': knowledge,
            'category': category,
            'added_at': datetime.now().isoformat()
        })

    def add_conversation(self, role: str, content: str):
        """
        添加对话历史

        Args:
            role: 角色 (user/assistant)
            content: 对话内容
        """
        self.conversation_history.append({
            'role': role,
            'content': content
        })

        # 保持历史记录在限制范围内
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []

    def get_messages(self, user_input: str, user_id: str = "default") -> List[Dict[str, str]]:
        """
        构建完整的消息列表（增强版，包含 Mem0 记忆）

        Args:
            user_input: 用户输入
            user_id: 用户ID（用于 Mem0 记忆检索）

        Returns:
            消息列表
        """
        # 1. 检索 Mem0 长期记忆
        mem0_context = ""
        if self.mem0_manager:
            mem0_context = self.mem0_manager.search_memories(
                query=user_input,
                user_id=user_id,
                limit=5
            )
            # 调试信息：显示检索到的记忆
            if mem0_context:
                print(f"[Mem0] 检索到 {len(mem0_context.split(chr(10)))} 条记忆")
                print(f"[Mem0] 记忆内容:\n{mem0_context}")
            else:
                print(f"[Mem0] 未检索到相关记忆（查询: {user_input}）")

        # 格式化用户信息
        user_info_str = self._format_user_info()

        # 格式化知识库
        knowledge_str = self._format_knowledge_base()

        # 构建系统提示（替换双大括号占位符）
        system_prompt = self.system_prompt.replace("{{current_time}}", datetime.now().strftime("%Y年%m月%d日 %H:%M"))
        system_prompt = system_prompt.replace("{{user_info}}", user_info_str)
        system_prompt = system_prompt.replace("{{knowledge_base}}", knowledge_str)

        # 2. 在系统提示中添加 Mem0 长期记忆
        if mem0_context:
            system_prompt += f"\n\n【长期记忆】（来自历史对话）\n{mem0_context}"
            print(f"[Mem0] 已将记忆注入到系统 Prompt")

        # 构建消息列表
        messages = [
            {'role': 'system', 'content': system_prompt}
        ]

        # 添加对话历史
        messages.extend(self.conversation_history)

        # 添加当前用户输入
        messages.append({'role': 'user', 'content': user_input})

        return messages

    def _format_user_info(self) -> str:
        """格式化用户信息"""
        if not self.user_info:
            return "暂无用户信息"

        parts = []

        if 'name' in self.user_info:
            parts.append(f"用户名：{self.user_info['name']}")

        if 'preferences' in self.user_info:
            prefs = self.user_info['preferences']
            if prefs:
                parts.append("偏好：" + "、".join(f"{k}={v}" for k, v in prefs.items()))

        if 'context' in self.user_info:
            ctx = self.user_info['context']
            if ctx:
                parts.append("上下文：" + "、".join(f"{k}={v}" for k, v in ctx.items()))

        return "\n".join(parts) if parts else "暂无用户信息"

    def _format_knowledge_base(self) -> str:
        """格式化知识库"""
        if not self.knowledge_base:
            return "暂无知识库信息"

        # 只显示最近的 5 条知识
        recent_knowledge = self.knowledge_base[-5:]

        parts = []
        for i, kb in enumerate(recent_knowledge, 1):
            category = f"[{kb['category']}] " if kb['category'] else ""
            parts.append(f"{i}. {category}{kb['content']}")

        return "\n".join(parts)

    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        if not self.conversation_history:
            return "暂无对话历史"

        summary = []
        for msg in self.conversation_history[-6:]:  # 最近 3 轮
            role = "用户" if msg['role'] == 'user' else "助手"
            content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            summary.append(f"{role}: {content}")

        return "\n".join(summary)


class VoiceAssistantConfig:
    """语音助手配置"""

    # 角色预设
    ROLES = {
        'default': {
            'name': '幽默助手',
            'personality': '风趣、搞笑、机智',
            'style': '幽默对话'
        },
        'friendly': {
            'name': '友好助手',
            'personality': '友好、专业、简洁',
            'style': '自然对话'
        },
        'casual': {
            'name': '轻松助手',
            'personality': '活泼、幽默、随和',
            'style': '轻松聊天'
        },
        'professional': {
            'name': '专业助手',
            'personality': '严谨、专业、高效',
            'style': '专业咨询'
        },
        'companion': {
            'name': '陪伴助手',
            'personality': '温暖、关心、耐心',
            'style': '情感陪伴'
        }
    }

    # 输出长度限制
    MAX_OUTPUT_LENGTH = {
        'short': 50,      # 简短回答
        'medium': 100,    # 中等回答
        'long': 200       # 较长回答
    }

    # 禁止的符号
    FORBIDDEN_SYMBOLS = [
        '**', '__', '###', '```', '---',
        '- ', '* ', '+ ',  # 列表符号
        '1. ', '2. ', '3. ',  # 编号列表
    ]
