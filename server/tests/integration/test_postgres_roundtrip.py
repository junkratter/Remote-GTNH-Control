"""Postgres compatibility: create schema via ORM and persist rows (ADR-006 B2)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

pytest.importorskip("testcontainers")

from testcontainers.postgres import PostgresContainer


def _docker_available() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture
def postgres_url() -> str:
    if not _docker_available():
        pytest.skip("Docker daemon not available (testcontainers needs Docker)")
    with PostgresContainer("postgres:16-alpine") as pg:
        raw = pg.get_connection_url(driver=None)
        yield raw.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest.mark.asyncio
async def test_postgres_task_roundtrip(postgres_url: str) -> None:
    """Main DB models insert/select on a live Postgres instance."""

    from app.db.base import Base
    from app.db.models import Task

    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Task(
                id="pg_rt_1",
                client_id="c1",
                commands=["return true"],
                status="ready",
                chunked=False,
            )
        )
        await session.commit()

    async with factory() as session:
        row = await session.get(Task, "pg_rt_1")
        assert row is not None
        assert row.client_id == "c1"

    await engine.dispose()


def test_migrate_sqlite_to_pg_script_smoke(tmp_path: Path, postgres_url: str) -> None:
    """``tools/migrate-sqlite-to-pg.py`` copies rows when target schema exists."""

    from app.db.base import Base
    from app.db.models import Task

    sqlite_path = tmp_path / "src.sqlite"
    eng_sql = create_engine(f"sqlite:///{sqlite_path}")
    Base.metadata.create_all(eng_sql)
    S = sessionmaker(eng_sql)
    with S() as s:
        s.add(
            Task(
                id="m1",
                client_id=None,
                commands=[],
                status="ready",
                chunked=False,
            )
        )
        s.commit()

    sync_pg = postgres_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    eng_pg = create_engine(sync_pg)
    Base.metadata.drop_all(eng_pg)
    Base.metadata.create_all(eng_pg)

    server_dir = Path(__file__).resolve().parents[2]
    script = server_dir.parent / "tools" / "migrate-sqlite-to-pg.py"
    env = {**os.environ, "PYTHONPATH": str(server_dir)}
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--sqlite",
            str(sqlite_path),
            "--pg-url",
            sync_pg,
        ],
        check=True,
        env=env,
        cwd=str(server_dir),
    )

    Sg = sessionmaker(eng_pg)
    with Sg() as s:
        row = s.execute(select(Task).where(Task.id == "m1")).scalar_one_or_none()
        assert row is not None
