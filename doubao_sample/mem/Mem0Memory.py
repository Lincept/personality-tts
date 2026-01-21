from mem0 import AsyncMemory
from mem0.configs.base import MemoryConfig
from dataclasses import asdict
from typing import Dict, List
import time
import logging
import pprint

from mem.base import BaseMemory
from schemas import Mem0Config, MemoryMeta
from config import mem0_config, memory_meta


logger = logging.getLogger(__name__)

class Mem0Memory(BaseMemory):

    def __init__(self, memory_meta: MemoryMeta = memory_meta, mem0_config: Mem0Config = mem0_config) -> None:
        self.memory_meta = memory_meta
        self.config = mem0_config
        self.client = AsyncMemory(config=MemoryConfig(**asdict(mem0_config)))

        self.message_pairs = {}
    
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
            await self.add_messages(session_id=session_id, messages=messages)
            del self.message_pairs[message_id]

    async def add_messages(self, session_id: str, messages: List[Dict]) -> Dict:
        """Add some messages to memory storage"""
        now_ts = int(time.time() * 1000)
        logger.info(f"Saving messages to Mem0Memory: {pprint.pformat(messages, indent=4)}")
        info = await self.client.add(
            messages=messages,
            user_id=self.memory_meta.user_id,
            agent_id=self.memory_meta.assistant_id,
            run_id=session_id,
            metadata={
                "time": now_ts,
            }
        )
        return info

    async def save_messages(self, session_id: str) -> Dict:
        """Save all messages from local cache to memory storage"""
        logger.warning("Mem0Memory does not support save_messages directly, use add_messages instead.")
        return {}

    async def search_profile(self) -> str:
        """Search user profile from memory storage"""
        result = await self.client.search(
            query="user profile, include base information, hobby, preference, occupation, etc.",
            user_id=self.memory_meta.user_id,
            agent_id=self.memory_meta.assistant_id,
            limit=1,
        )
        result = "\n".join([ r["content"] for r in result["results"]])

        return result
    
    async def search_events_by_query(self, query: str, limit: int = 3) -> str:
        """Search events by query from memory storage"""
        result = await self.client.search(
            query=query,
            user_id=self.memory_meta.user_id,
            agent_id=self.memory_meta.assistant_id,
            limit=limit,
        )
        result = "\n".join([ r["memory"] for r in result["results"]])

        return result

    async def search_recent_events(self, days_ago: int = 1, limit: int = 10) -> str:
        """Search recent events from memory storage"""
        # Get current timestamp in milliseconds
        current_time = int(time.time() * 1000)
        one_day_ago = current_time - days_ago * 24 * 60 * 60 * 1000
        
        result = await self.client.get_all(
            user_id=self.memory_meta.user_id,
            agent_id=self.memory_meta.assistant_id,
            filters={
                "time": {"gt": one_day_ago}
            },
            limit=limit,
        )
        result = "\n".join([ r["memory"] for r in result["results"]])

        return result