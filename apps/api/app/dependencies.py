from collections.abc import AsyncIterator

from arq.connections import ArqRedis, RedisSettings, create_pool
from redis.asyncio import Redis

from apps.api.app.config import get_settings

settings = get_settings()
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_job_queue() -> AsyncIterator[ArqRedis]:
    queue = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        yield queue
    finally:
        await queue.aclose()
