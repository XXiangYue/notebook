from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.api.app.config import get_settings
from apps.api.app.database import engine
from apps.api.app.dependencies import redis_client
from apps.api.app.routers.categories import router as categories_router
from apps.api.app.routers.ingestion import router as ingestion_router
from apps.api.app.routers.knowledge import router as knowledge_router
from apps.api.app.routers.search import router as search_router
from apps.api.app.routers.settings import router as settings_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await redis_client.aclose()
        await engine.dispose()


app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(knowledge_router)
app.include_router(categories_router)
app.include_router(ingestion_router)
app.include_router(search_router)
app.include_router(settings_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs"}


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def ready(response: Response) -> dict[str, Any]:
    checks = {"database": False, "redis": False}

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = True
    except SQLAlchemyError:
        pass

    with suppress(RedisError):
        checks["redis"] = bool(await redis_client.ping())

    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ok" if is_ready else "unavailable", "checks": checks}
