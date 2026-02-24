"""
Wrapper around mem0 usage.

This file provides two patterns:
1) Using a remote MemoryClient with an API key (MemoryClient)
2) Using Memory.from_config with a LangChain model instance (in-process)

Replace the placeholders with your actual mem0 usage and configuration.
"""
from typing import List, Dict, Optional
from app.config.settings import settings

# Try to import MemoryClient from mem0 SDK if available
try:
    from mem0 import MemoryClient, Memory
except Exception:
    MemoryClient = None
    Memory = None

class Mem0Wrapper:
    def __init__(self):
        # If you have a remote mem0 instance and API key, use MemoryClient
        if MemoryClient and settings.mem0_api_key:
            self.client = MemoryClient(api_key=settings.mem0_api_key)
            self.mode = "client"
        else:
            # As fallback, use in-process Memory if available (requires Memory.from_config)
            self.client = None
            self.mode = "none"

    def search(self, query: str, user_id: str, limit: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """Return list of memory dicts: [{'memory': '...', 'score': 0.9}, ...]"""
        if self.mode == "client":
            return self.client.search(query, user_id=user_id, limit=limit, filters=filters)
        # Fallback: return empty list so the app still works offline
        return []

    def add(self, messages: List[Dict], user_id: str, metadata: Optional[Dict] = None):
        if self.mode == "client":
            return self.client.add(messages, user_id=user_id, metadata=metadata or {})
        return None

mem0 = Mem0Wrapper()
