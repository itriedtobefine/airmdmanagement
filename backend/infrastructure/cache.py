import redis.asyncio as redis
from core.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)


async def get_redis() -> redis.Redis:
    return redis_client
