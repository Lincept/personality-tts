"""
事件层 - 管理活动摘要和事件存储
"""
import json
import os
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from ..models.event import Event, EventType, DailySummary


class EventLayer:
    """事件管理器"""

    def __init__(
        self,
        agent_id: str,
        mem0_manager=None,
        summary_dir: str = "data/context/event_summaries",
        llm_client=None
    ):
        """
        初始化事件管理器

        Args:
            agent_id: Agent 标识
            mem0_manager: Mem0 管理器（用于事件向量存储）
            summary_dir: 摘要存储目录
            llm_client: LLM 客户端（用于生成摘要）
        """
        self.agent_id = agent_id
        self.mem0 = mem0_manager
        self.summary_dir = summary_dir
        self.llm_client = llm_client

        # 内存中的对话缓存（用于批量处理）
        self._conversation_buffer: List[Dict[str, str]] = []

        # 内存中的今日事件缓存
        self._today_events: List[Event] = []

        # 加载今日摘要
        self.today_summary = self._load_or_create_summary(date.today())

    def _load_or_create_summary(self, target_date: date) -> DailySummary:
        """加载或创建每日摘要"""
        summary_file = os.path.join(
            self.summary_dir,
            f"{self.agent_id}_{target_date.isoformat()}.json"
        )

        if os.path.exists(summary_file):
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return DailySummary.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass

        return DailySummary(date=target_date, agent_id=self.agent_id)

    def add_conversation_to_buffer(self, user_input: str, assistant_response: str, user_id: str):
        """
        将对话添加到缓存（等待批量处理）

        Args:
            user_input: 用户输入
            assistant_response: 助手回复
            user_id: 用户ID
        """
        self._conversation_buffer.append({
            "user_input": user_input,
            "assistant_response": assistant_response,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })

        # 更新统计
        self.today_summary.total_messages += 2

        if user_id not in self.today_summary.unique_users:
            self.today_summary.unique_users.append(user_id)

    def process_batch(self):
        """
        批量处理缓存的对话

        这个方法会：
        1. 从对话中抽取事件
        2. 存储重要事件到 Mem0
        3. 更新活动摘要
        """
        if not self._conversation_buffer:
            return

        # 抽取事件
        events = self._extract_events_from_buffer()

        # 存储重要事件
        for event in events:
            self._today_events.append(event)
            if event.importance > 0.5 and self.mem0:
                self._store_event_to_mem0(event)

        # 更新活动摘要
        self._regenerate_summary_text()

        # 增加对话计数
        self.today_summary.total_conversations += len(self._conversation_buffer)

        # 清空缓存
        self._conversation_buffer = []

    def _extract_events_from_buffer(self) -> List[Event]:
        """从缓存的对话中抽取事件"""
        if not self.llm_client or not self._conversation_buffer:
            return []

        # 构建对话文本
        conv_text = ""
        for conv in self._conversation_buffer[-10:]:  # 最近10条
            conv_text += f"用户: {conv['user_input']}\n"
            conv_text += f"助手: {conv['assistant_response']}\n\n"

        prompt = f"""分析以下对话，提取值得记录的关键事件。

{conv_text}

如果有值得记录的事件（如：用户分享了重要信息、有特殊情感表达、达成了某个目标等），
请以 JSON 格式返回：
{{
    "events": [
        {{"type": "事件类型", "content": "事件描述", "importance": 0.5}}
    ]
}}

如果没有特别值得记录的事件，返回：{{"events": []}}

事件类型可选：conversation, learning, emotional, task, milestone
importance 范围：0.0-1.0（0.7以上为重要事件）"""

        try:
            # 调用 LLM
            response = self.llm_client.chat.completions.create(
                model=self.llm_client.model if hasattr(self.llm_client, 'model') else "qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是一个事件抽取助手，从对话中识别关键事件。只输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)

            events = []
            for event_data in result.get("events", []):
                user_id = self._conversation_buffer[-1]["user_id"] if self._conversation_buffer else "unknown"
                event = Event(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.from_string(event_data.get("type", "conversation")),
                    content=event_data.get("content", ""),
                    timestamp=datetime.now(),
                    participants=[user_id],
                    importance=event_data.get("importance", 0.5)
                )
                events.append(event)

            return events

        except Exception as e:
            print(f"[EventLayer] 事件抽取失败: {e}")
            return []

    def _store_event_to_mem0(self, event: Event):
        """将事件存储到 Mem0 向量数据库"""
        if not self.mem0 or not hasattr(self.mem0, 'memory'):
            return

        try:
            # 构建带时间戳的事件描述
            event_text = event.to_mem0_format()

            # 存储到 Mem0，使用 agent_id 作为 user_id
            self.mem0.memory.add(
                event_text,
                user_id=f"agent_events_{self.agent_id}",
                metadata={
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "importance": event.importance
                }
            )
        except Exception as e:
            print(f"[EventLayer] 事件存储失败: {e}")

    def _regenerate_summary_text(self):
        """使用 LLM 重新生成摘要文本"""
        if not self.llm_client:
            # 简单拼接
            if self._today_events:
                events_text = "；".join([e.content for e in self._today_events[-5:]])
                self.today_summary.summary_text = f"今天{events_text}"
            return

        # 收集素材
        events_text = "\n".join([
            f"- [{e.timestamp.strftime('%H:%M')}] {e.content}"
            for e in self._today_events[-20:]
        ])

        if not events_text:
            events_text = "今天还没有特别的事情发生"

        prompt = f"""根据以下事件，生成一段简短的活动摘要（2-3句话）：

{events_text}

要求：
1. 使用第一人称
2. 概括主要活动和互动
3. 自然口语化，像在跟朋友说"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_client.model if hasattr(self.llm_client, 'model') else "qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是一个摘要生成助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            self.today_summary.summary_text = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[EventLayer] 摘要生成失败: {e}")

    def search_events(self, query: str, time_range: Optional[str] = None) -> List[str]:
        """
        搜索历史事件

        Args:
            query: 搜索查询
            time_range: 时间范围描述（如 "上周", "昨天", "最近三天"）

        Returns:
            相关事件描述列表
        """
        if not self.mem0 or not hasattr(self.mem0, 'memory'):
            return []

        # 构建包含时间信息的查询
        search_query = query
        if time_range:
            search_query = f"{time_range} {query}"

        try:
            results = self.mem0.memory.search(
                query=search_query,
                user_id=f"agent_events_{self.agent_id}",
                limit=10
            )

            if not results.get("results"):
                return []

            return [r["memory"] for r in results["results"]]

        except Exception as e:
            print(f"[EventLayer] 事件搜索失败: {e}")
            return []

    def save_summary(self):
        """保存今日摘要"""
        os.makedirs(self.summary_dir, exist_ok=True)
        summary_file = os.path.join(
            self.summary_dir,
            f"{self.agent_id}_{self.today_summary.date.isoformat()}.json"
        )

        # 将事件也保存
        self.today_summary.key_events = self._today_events[-20:]

        data = self.today_summary.to_dict()

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generate_event_context(self) -> str:
        """生成事件层的上下文字符串"""
        return self.today_summary.to_context_string()

    def get_buffer_size(self) -> int:
        """获取当前缓存的对话数量"""
        return len(self._conversation_buffer)
