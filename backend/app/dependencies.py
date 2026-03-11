"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

_engine = create_async_engine(settings.POSTGRES_URL, echo=settings.is_development)
_async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)

_redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = aioredis.Redis(connection_pool=_redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
