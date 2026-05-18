"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator

os.environ.setdefault("SERVER_TOKEN", "test-token")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _set_db_envs(path: str) -> None:
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{path}"


@pytest.fixture(scope="session")
def db_path() -> str:
    fd, path = tempfile.mkstemp(prefix="gtnh-cyber-test-", suffix=".sqlite")
    os.close(fd)
    _set_db_envs(path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest_asyncio.fixture(scope="session")
async def app(db_path: str):
    # Importing after envs are patched ensures settings pick up the test DB.
    from app.db.base import Base
    from app.main import create_app

    application = create_app()

    from app.db.session import engine as app_engine

    async with app_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Server-Token": "test-token"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def anon_client(app) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
