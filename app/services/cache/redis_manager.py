# app/services/redis_manager.py
import os
import redis
import json
import functools
from typing import Optional

# Connection setup
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "redis://localhost:6379")

r = redis.Redis.from_url("rediss://default:AXAUAAIncDIwYmNmODRkYWU5MmY0MmQ4OGZjYTRkZTRhNzlmMjI0MnAyMjg2OTI@loyal-mosquito-28692.upstash.io:6379")


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