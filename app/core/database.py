import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

# Async engine — asyncpg driver required
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # set True for SQL query logging during development
    pool_pre_ping=True,  # reconnect on stale connections
)

# CRITICAL: expire_on_commit=False prevents MissingGreenlet on post-commit attribute access
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
