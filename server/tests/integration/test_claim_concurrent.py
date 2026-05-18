"""Concurrent / sequential claims on the task queue (plan B3)."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import PENDING, READY
from app.core.tasks import task_store


@pytest.mark.asyncio
async def test_two_clients_claim_distinct_ready_tasks_sqlite(app) -> None:
    """SQLite branch: sequential claims hand out different READY rows."""

    from app.db.models import Task
    from app.db.session import AsyncSessionLocal

    a_id = f"claim_{uuid.uuid4().hex[:10]}_a"
    b_id = f"claim_{uuid.uuid4().hex[:10]}_b"

    async with AsyncSessionLocal() as session:
        session.add(
            Task(id=a_id, client_id=None, commands=["a"], status=READY, chunked=False)
        )
        session.add(
            Task(id=b_id, client_id=None, commands=["b"], status=READY, chunked=False)
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        a = await task_store.claim_next(session, client_id="robot-A")
        b = await task_store.claim_next(session, client_id="robot-B")
    assert a is not None and b is not None
    assert a.id != b.id
    assert {a.id, b.id} == {a_id, b_id}
    assert a.status == PENDING and b.status == PENDING


@pytest.mark.asyncio
async def test_same_client_id_second_claim_sees_remaining_ready_sqlite(app) -> None:
    """One client receives at most one task per successful claim; next call gets another READY."""

    from app.db.models import Task
    from app.db.session import AsyncSessionLocal

    u1 = f"claim_{uuid.uuid4().hex[:10]}_u1"
    u2 = f"claim_{uuid.uuid4().hex[:10]}_u2"

    async with AsyncSessionLocal() as session:
        session.add(
            Task(id=u1, client_id=None, commands=["x"], status=READY, chunked=False)
        )
        session.add(
            Task(id=u2, client_id=None, commands=["y"], status=READY, chunked=False)
        )
        await session.commit()

    cid = "same-robot"
    async with AsyncSessionLocal() as session:
        first = await task_store.claim_next(session, client_id=cid)
    assert first is not None

    async with AsyncSessionLocal() as session:
        second = await task_store.claim_next(session, client_id=cid)
    assert second is not None
    assert first.id != second.id
    assert {first.id, second.id} == {u1, u2}


def _docker_available() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture
def postgres_url() -> str:
    pytest.importorskip("testcontainers")
    if not _docker_available():
        pytest.skip("Docker daemon not available (testcontainers needs Docker)")
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        raw = pg.get_connection_url(driver=None)
        yield raw.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest.mark.asyncio
async def test_parallel_claims_postgres_skip_locked(postgres_url: str) -> None:
    """Postgres: concurrent claim_next with SKIP_LOCKED — N workers take N distinct tasks."""

    from app.db.base import Base
    from app.db.models import Task

    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    n = 8
    async with factory() as session:
        for i in range(n):
            session.add(
                Task(
                    id=f"pg_claim_{i}",
                    client_id=None,
                    commands=[f"c{i}"],
                    status=READY,
                    chunked=False,
                )
            )
        await session.commit()

    barrier = asyncio.Barrier(n)

    async def worker(worker_id: int) -> str:
        await barrier.wait()
        async with factory() as session:
            t = await task_store.claim_next(session, client_id=f"worker-{worker_id}")
        assert t is not None
        assert t.status == PENDING
        return t.id

    ids = await asyncio.gather(*[worker(i) for i in range(n)])
    assert len(set(ids)) == n

    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_respects_client_scoped_ready_task_sqlite(app) -> None:
    """Task with client_id set is only visible to that client."""

    from app.db.models import Task
    from app.db.session import AsyncSessionLocal

    scoped_id = f"claim_scoped_{uuid.uuid4().hex[:10]}"

    async with AsyncSessionLocal() as session:
        session.add(
            Task(
                id=scoped_id,
                client_id="owner",
                commands=["z"],
                status=READY,
                chunked=False,
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        wrong = await task_store.claim_next(session, client_id="intruder")
    assert wrong is None

    async with AsyncSessionLocal() as session:
        ok = await task_store.claim_next(session, client_id="owner")
    assert ok is not None
    assert ok.id == scoped_id
