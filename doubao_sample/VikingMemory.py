import time
from typing import List, Dict, Optional
from vikingdb import IAM, VikingMem
from vikingdb.memory.exceptions import VikingMemException

import config

class VikingMemory:
    def __init__(self) -> None:
        self._auth = IAM(
            ak=config.VIKINGDB_AK,
            sk=config.VIKINGDB_SK
        )
        self.client = VikingMem(
            host="api-knowledgebase.mlp.cn-beijing.volces.com",
            region="cn-beijing",
            auth=self._auth,
            scheme="http",
        )
        try:
            self.client.ping()
        except VikingMemException as e:
            if config.ENABLE_LOG:
                print("VikingMemory initialize error: {e}")
        self.collection = self.client.get_collection(
            collection_name=config.VIKINGDB_COLLECTION
        )

    async def save_memory(self, session_id: str, messages: List[Dict]):
        if len(messages) == 0 or len(messages) > 100:
            print("Viking: length of messages(role without system) must 1-100, skip save.")
            return
        now_ts = int(time.time() * 1000)
        metadata = {
            "default_user_id": config.VIKINGDB_USER_ID,
            "default_user_name": config.VIKINGDB_USER_NAME,
            "default_assistant_id": config.VIKINGDB_ASSISTANT_ID,
            "default_assistant_name": config.VIKINGDB_ASSISTANT_NAME,
            # "group_id": "",
            "time": now_ts,
        }
        # Add session messages
        session_info = await self.collection.async_add_session(
            session_id = session_id,
            messages = messages,
            metadata = metadata
        )
        return session_info

    async def search_profile(self) -> str:
        
        result = await self.collection.async_search_memory(
            filter = {
                "user_id": config.VIKINGDB_USER_ID,
                "assistant_id": config.VIKINGDB_ASSISTANT_ID,
                "memory_type": ["profile_v1"],
            },
            limit=1
        )

        return result['data']['result_list'][0]['memory_info']['user_profile']
    
    async def search_events_by_query(self, query: str, limit: int = 3) -> str:
        
        result = await self.collection.async_search_memory(
            query=query,
            filter = {
                "user_id": config.VIKINGDB_USER_ID,
                "assistant_id": config.VIKINGDB_ASSISTANT_ID,
                "memory_type": ["event_v1"],  # Search for event type
            },
            limit=limit
        )
        result = "\n".join([r['memory_info']['summary'] for r in result['data']['result_list']])

        return result
    
    async def search_recent_events(self, days_ago: int = 1, limit: int = 10) -> str:
        """Search recent events with time range filter"""

        # Get current timestamp in milliseconds
        current_time = int(time.time() * 1000)
        
        # Search events from last 24 hours
        one_day_ago = current_time - days_ago * 24 * 60 * 60 * 1000
        
        result = await self.collection.async_search_memory(
            filter = {
                "user_id": config.VIKINGDB_USER_ID,
                "assistant_id": config.VIKINGDB_ASSISTANT_ID,
                "memory_type": ["event_v1"],  # Search for event type
                "start_time": one_day_ago,  # Start time in milliseconds
                "end_time": current_time,    # End time in milliseconds
            },
            limit=limit
        )
        result = "\n".join([r['memory_info']['summary'] for r in result['data']['result_list']])

        return result
    
import json
from typing import Any, Dict, List, Optional


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _truncate_items(items: List[Dict[str, str]], max_chars: int) -> str:
    if not items:
        return "[]"
    payload = json.dumps(items, ensure_ascii=False)
    if len(payload) <= max_chars:
        return payload

    trimmed = [dict(item) for item in items]
    while trimmed and len(json.dumps(trimmed, ensure_ascii=False)) > max_chars:
        last = trimmed[-1]
        content = last.get("content", "")
        if len(content) > 80:
            last["content"] = content[:-200]
        else:
            trimmed.pop()
    return json.dumps(trimmed, ensure_ascii=False)


async def build_external_rag_payload(
    memory_client: Any,
    query: str,
    profile_cache: Optional[Any] = None,
    max_items: int = 3,
    max_chars: int = 3800,
) -> str:
    """
    生成ChatRAGText所需的external_rag JSON数组字符串。
    约束：总长度不超过4K字符。
    """
    items: List[Dict[str, str]] = []

    profile = profile_cache
    if profile is None:
        try:
            profile = await memory_client.search_profile()
        except Exception:
            profile = None

    if profile is not None:
        items.append({
            "title": "用户画像",
            "content": _to_text(profile),
        })

    try:
        events = await memory_client.search_events_by_query(query, limit=2)
    except Exception:
        events = None

    if events is not None:
        items.append({
            "title": "相关事件",
            "content": _to_text(events),
        })

    if not items:
        return "[]"

    items = items[:max_items]
    return _truncate_items(items, max_chars)

