from abc import ABC, abstractmethod
from typing import Dict

class BaseMemory(ABC):

    @abstractmethod
    async def insert_message(self, message_id: str, role: str, content: str, session_id: str = ""):
        """Insert a single message pair to local cache"""
        pass

    @abstractmethod
    async def add_messages(self, session_id: str, messages: list) -> Dict:
        """Add some messages to memory storage"""
        pass

    @abstractmethod
    async def save_messages(self, session_id: str) -> Dict:
        """Save all messages from local cache to memory storage"""
        pass

    @abstractmethod
    async def search_profile(self) -> str:
        """Search user profile from memory storage"""
        pass

    @abstractmethod
    async def search_events_by_query(self, query: str, limit: int = 3) -> str:
        """Search events by query from memory storage"""
        pass

    @abstractmethod
    async def search_recent_events(self, days_ago: int = 1, limit: int = 10) -> str:
        """Search recent events from memory storage"""
        pass