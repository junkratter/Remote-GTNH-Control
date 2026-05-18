"""SQLAlchemy async engine + session factory + FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import settings


def make_engine(url: str | None = None) -> AsyncEngine:
    """Create a new async engine.

    SQLite needs `check_same_thread=False`; for other backends extra kwargs
    can be appended here.
    """

    target_url = url or settings.database_url
    connect_args: dict[str, object] = {}
    if target_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(target_url, echo=False, connect_args=connect_args)


engine: AsyncEngine = make_engine()
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async DB session."""

    async with AsyncSessionLocal() as session:
        yield session
