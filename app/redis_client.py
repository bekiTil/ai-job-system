import os
import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

redis_client = redis.from_url(f"{REDIS_URL}/1", decode_responses=True)