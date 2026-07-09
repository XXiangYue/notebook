import os
from collections.abc import AsyncIterator

os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["EMBEDDING_MODEL"] = "local-hash-embedding-v1"
os.environ["EMBEDDING_DIMENSIONS"] = "1536"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apps.api.app.database import get_session
from apps.api.app.dependencies import get_job_queue
from apps.api.app.main import app
from apps.api.app.models import Base


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    class FakeQueue:
        async def enqueue_job(self, *_: object, **__: object) -> object:
            return object()

    async def override_get_job_queue() -> AsyncIterator[FakeQueue]:
        yield FakeQueue()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_job_queue] = override_get_job_queue
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
