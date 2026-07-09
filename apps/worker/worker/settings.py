from uuid import UUID

from arq.connections import RedisSettings

from apps.api.app.config import get_settings
from apps.api.app.database import async_session_factory, engine
from apps.api.app.services.ingestion import process_organize_job


async def organize_knowledge(_: dict, job_id: str) -> None:
    async with async_session_factory() as session:
        await process_organize_job(session, UUID(job_id))


async def shutdown(_: dict) -> None:
    await engine.dispose()


settings = get_settings()


class WorkerSettings:
    functions = [organize_knowledge]
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    health_check_interval = 30
