# app/services/redis_manager.py
import os
import redis
import json
import functools
from typing import Optional

# Connection setup
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

r = redis.from_url(REDIS_URL, decode_responses=True)

class CacheManager:
    @staticmethod
    async def get(key: str) -> Optional[dict]:
        """Retrieve data from Redis"""
        data = r.get(key)
        print(f"Data keys {data}")
        return json.loads(data) if data else None

    @staticmethod
    async def set(key: str, data: dict, expire: int = 3600):
        """Store data in Redis with 1-hour default expiry"""
        r.setex(key, expire, json.dumps(data))

    @staticmethod
    async def clear(key: str):
        """Manually invalidate cache"""
        r.delete(key)