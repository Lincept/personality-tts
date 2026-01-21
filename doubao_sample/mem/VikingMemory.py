import logging
import time
import pprint
from typing import Dict
from mem.base import BaseMemory
from vikingdb import IAM, VikingMem
from vikingdb.memory.exceptions import VikingMemException
from schemas import VikingConfig, MemoryMeta
from config import viking_config, memory_meta

logger = logging.getLogger(__name__)

class VikingMemory(BaseMemory):
    def __init__(self, memory_meta: MemoryMeta = memory_meta, viking_config: VikingConfig = viking_config) -> None:
        self.memory_meta = memory_meta
        self.config = viking_config
        self._auth = IAM(
            ak=viking_config.ak,
            sk=viking_config.sk
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
            logger.error(f"VikingMemory initialize error: {e}")
        self.collection = self.client.get_collection(
            collection_name=self.memory_meta.collection
        )

        self.message_pairs = {}
        self.message_list = []

    async def insert_message(self, message_id: str, role: str, content: str, session_id: str = ""):
        """Insert a single message pair to local cache"""
        if role not in ["user", "assistant"]:
            logger.warning("Viking: role must be one of user, assistant, system. skip save. ")
            return
        if message_id not in self.message_pairs:
            self.message_pairs[message_id] = {}
        self.message_pairs[message_id][role] = content
        if "user" in self.message_pairs[message_id] and "assistant" in self.message_pairs[message_id]:
            messages = [
                {
                    "role": "user",
                    "content": self.message_pairs[message_id]["user"]
                },
                {
                    "role": "assistant",
                    "content": self.message_pairs[message_id]["assistant"]
                }
            ]
            self.message_list.extend(messages)
            del self.message_pairs[message_id]

    async def add_messages(self, session_id: str, messages: list) -> Dict:
        """Add some messages to memory storage"""
        logger.warning("VikingMemory does not support add_messages directly, use save_messages instead.")
        return {}

    async def save_messages(self, session_id: str) -> Dict:
        """Save all messages from local cache to memory storage"""
        if len(self.message_list) == 0:
            return {}

        now_ts = int(time.time() * 1000)
        metadata = {
            "default_user_id": self.memory_meta.user_id,
            "default_assistant_id": self.memory_meta.assistant_id,
            "default_user_name": self.memory_meta.user_name,
            "default_assistant_name": self.memory_meta.assistant_name,
            # "group_id": "",
            "time": now_ts,
        }
        logger.info("Saving messages to VikingMemory:")
        logger.info("================================================================")
        logger.info(pprint.pformat(self.message_list, indent=4))
        logger.info("================================================================")
        session_info = await self.collection.async_add_session(
            session_id = session_id,
            messages = self.message_list,
            metadata = metadata
        )
        return session_info

    async def search_profile(self) -> str:
        """Search user profile from memory storage"""
        result = await self.collection.async_search_memory(
            filter = {
                "user_id": self.memory_meta.user_id,
                "assistant_id": self.memory_meta.assistant_id,
                "memory_type": ["profile_v1"],
            },
            limit=1
        )

        return result['data']['result_list'][0]['memory_info']['user_profile']
    
    async def search_events_by_query(self, query: str, limit: int = 3) -> str:
        """Search events by query from memory storage"""
        result = await self.collection.async_search_memory(
            query=query,
            filter = {
                "user_id": self.memory_meta.user_id,
                "assistant_id": self.memory_meta.assistant_id,
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
                "user_id": self.memory_meta.user_id,
                "assistant_id": self.memory_meta.assistant_id,
                "memory_type": ["event_v1"],  # Search for event type
                "start_time": one_day_ago,  # Start time in milliseconds
                "end_time": current_time,    # End time in milliseconds
            },
            limit=limit
        )
        result = "\n".join([r['memory_info']['summary'] for r in result['data']['result_list']])

        return result

