from .base import BaseMemory
from .utils import build_external_rag_payload
from .VikingMemory import VikingMemory
from .Mem0Memory import Mem0Memory

__all__ = [
    "BaseMemory",
    "build_external_rag_payload",
]

class NullMemory(BaseMemory):

    async def insert_message(self, message_id: str, role: str, content: str, session_id: str = "", mode: str = "override"):
        """Insert a single message pair to local cache"""
        pass

    async def add_messages(self, session_id: str, messages: list) -> dict:
        """Add some messages to memory storage"""
        return {}

    async def save_messages(self, session_id: str) -> dict:
        """Save all messages from local cache to memory storage"""
        return {}

    async def search_profile(self) -> str:
        """Search user profile from memory storage"""
        return ""

    async def search_events_by_query(self, query: str, limit: int = 3) -> str:
        """Search events by query from memory storage"""
        return ""

    async def search_recent_events(self, days_ago: int = 1, limit: int = 10) -> str:
        """Search recent events from memory storage"""
        return ""

def get_memory_instance(memory_backend: str) -> BaseMemory:
    """根据 memory_backend 创建对应的记忆实例。"""
    backend = memory_backend.strip().lower()
    if backend == "viking":
        return VikingMemory()
    elif backend == "mem0":
        return Mem0Memory()
    else:
        return NullMemory()