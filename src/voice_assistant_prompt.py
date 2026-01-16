"""
语音助手 Prompt 管理系统
包括角色设定、用户信息、知识库、对话历史管理
"""
from typing import List, Dict, Optional
from datetime import datetime


class VoiceAssistantPrompt:
    """语音助手 Prompt 管理器"""

    def __init__(self, role: str = "default", role_config: Optional[Dict] = None, mem0_manager=None, role_loader=None):
        """
        初始化 Prompt 管理器

        Args:
            role: 角色类型
            role_config: 自定义角色配置（从 role_loader 加载）
            mem0_manager: Mem0 记忆管理器（可选）
            role_loader: 角色加载器（可选）
        """
        self.role = role
        self.custom_role_config = role_config  # 保存自定义角色配置
        self.role_loader = role_loader  # 角色加载器
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

【对话思维框架】

每次回复前，先快速思考三个问题：
1. 用户现在的状态是什么？（兴奋/疲惫/好奇/敷衍/无聊）
2. 这个话题用户感兴趣吗？（从回复长度、语气判断）
3. 我应该怎么回应？（深入/转移/闲聊/倾听）

【核心原则】

• 语音对话：纯文本，不用任何符号（*#-等）、不分点、不列表
• 简短自然：2-3句话，像朋友聊天，不是客服问答
• 观察反应：用户敷衍就换话题，别死磕一个问题
• 称呼自然：知道名字偶尔叫，别每句都叫
• 记忆工具：用户分享重要信息时用 save_memories，需要回忆时用 search_memories

【对话策略】

根据用户状态选择：

• 用户主动分享 → 倾听 + 简短回应 + 适度追问
  例："我最近在学吉他" → "吉他挺有意思的，学多久了？"

• 用户回复简短/敷衍 → 不追问，换轻松话题或等待
  例："嗯" → "那咱随便聊聊吧" 或 "好的"

• 用户问问题 → 直接答，别展开太多
  例："Python 是什么" → "一种编程语言，挺好学的。你想学编程吗？"

• 闲聊状态 → 轻松聊，别总问问题，可以分享观点
  例："今天天气不错" → "是啊，这种天气最舒服了"

【当前时间】{{current_time}}
【用户信息】{{user_info}}
【知识库】{{knowledge_base}}

记住：像真人一样对话，观察用户意愿，灵活调整。"""
        else:
            # 使用普通字符串而不是 f-string，保留占位符
            base_prompt = """你是 {name}，一个{personality}的语音助手。

【对话思维框架】

每次回复前，先快速思考三个问题：
1. 用户现在的状态是什么？（兴奋/疲惫/好奇/敷衍/无聊）
2. 这个话题用户感兴趣吗？（从回复长度、语气判断）
3. 我应该怎么回应？（深入/转移/闲聊/倾听）

【核心原则】

• 语音对话：纯文本，不用任何符号（*#-等）、不分点、不列表
• 简短自然：2-3句话，像朋友聊天，不是客服问答
• 观察反应：用户敷衍就换话题，别死磕一个问题
• 称呼自然：知道名字偶尔叫，别每句都叫
• 记忆工具：用户分享重要信息时用 save_memories，需要回忆时用 search_memories

【对话策略】

根据用户状态选择：

• 用户主动分享 → 倾听 + 简短回应 + 适度追问
  例："我最近在学吉他" → "吉他挺有意思的，学多久了？"

• 用户回复简短/敷衍 → 不追问，换轻松话题或等待
  例："嗯" → "那咱随便聊聊吧" 或 "好的"

• 用户问问题 → 直接答，别展开太多
  例："Python 是什么" → "一种编程语言，挺好学的。你想学编程吗？"

• 闲聊状态 → 轻松聊，别总问问题，可以分享观点
  例："今天天气不错" → "是啊，这种天气最舒服了"

【当前时间】{{current_time}}
【用户信息】{{user_info}}
【知识库】{{knowledge_base}}

记住：像真人一样对话，观察用户意愿，灵活调整。"""

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
            role: 角色ID
        """
        # 优先从 role_loader 加载
        if self.role_loader:
            role_config = self.role_loader.get_role(role)
            if role_config:
                self.role = role
                self.custom_role_config = role_config
                self.system_prompt = self._build_system_prompt()
                return
            else:
                available = self.role_loader.get_role_ids()
                raise ValueError(f"未知角色: {role}，可选: {available}")

        # 降级到内置角色
        if role not in VoiceAssistantConfig.ROLES:
            raise ValueError(f"未知角色: {role}，可选: {list(VoiceAssistantConfig.ROLES.keys())}")

        self.role = role
        self.custom_role_config = None
        self.system_prompt = self._build_system_prompt()

    def get_role_info(self) -> Dict:
        """获取当前角色信息"""
        # 优先返回自定义角色配置
        if self.custom_role_config:
            return self.custom_role_config
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

    def get_messages(self, user_input: str, user_id: str = None) -> List[Dict[str, str]]:
        """
        构建完整的消息列表（自动检索相关记忆）

        Args:
            user_input: 用户输入
            user_id: 用户ID（用于检索记忆）

        Returns:
            消息列表
        """
        # 格式化用户信息
        user_info_str = self._format_user_info()

        # 格式化知识库
        knowledge_str = self._format_knowledge_base()

        # 构建系统提示（替换双大括号占位符）
        system_prompt = self.system_prompt.replace("{{current_time}}", datetime.now().strftime("%Y年%m月%d日 %H:%M"))
        system_prompt = system_prompt.replace("{{user_info}}", user_info_str)
        system_prompt = system_prompt.replace("{{knowledge_base}}", knowledge_str)

        # 自动检索相关记忆（如果启用了 Mem0）
        if user_id and self.mem0_manager and self.mem0_manager.enabled:
            relevant_memories = self.mem0_manager.search_memories(
                query=user_input,
                user_id=user_id,
                limit=5
            )

            if relevant_memories:
                # 将记忆添加到系统提示
                system_prompt += f"\n\n【相关记忆】\n{relevant_memories}"

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

    # 默认角色（仅作为 fallback，实际角色从 roles/ 目录加载）
    ROLES = {
        'default': {
            'name': '默认助手',
            'personality': '友好、专业',
            'style': '自然对话'
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
