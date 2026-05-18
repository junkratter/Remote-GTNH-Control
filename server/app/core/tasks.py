"""SQLAlchemy-backed task store.

Replaces the legacy `utils/task.py` (which stored each task as a file in
`tasks/<task_id>.json`). External interface stays identical so the OC
client and existing logic continues to work.

The store exposes both `async` (preferred, used in FastAPI routes) and
`sync` shims (used by APScheduler / threaded triggers from `automation/`).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import COMPLETED, PENDING, READY
from app.core.logging import logger
from app.core.settings import settings
from app.db.models import Task, TaskHistory
from app.db.session import AsyncSessionLocal


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value else None


def _to_dict(task: Task) -> dict[str, Any]:
    """Backwards-compat view that matches the legacy file format."""

    return {
        "client_id": task.client_id,
        "commands": list(task.commands or []),
        "status": task.status,
        "chunked": task.chunked,
        "results": task.results,
        "created_time": _iso(task.created_time),
        "pending_time": _iso(task.pending_time),
        "completed_time": _iso(task.completed_time),
    }


class TaskStore:
    """Async SQLA-backed CRUD over the `tasks` table."""

    async def add(
        self,
        session: AsyncSession,
        task_id: str,
        client_id: str | None,
        commands: Iterable[str],
        status: str = READY,
        is_chunked: bool = False,
    ) -> Task:
        task = await session.get(Task, task_id)
        commands_list = list(commands)
        if task is None:
            task = Task(
                id=task_id,
                client_id=client_id,
                commands=commands_list,
                status=status,
                chunked=is_chunked,
                created_time=_now(),
            )
            session.add(task)
        else:
            task.client_id = client_id
            task.commands = commands_list
            task.status = status
            task.chunked = is_chunked
            task.created_time = _now()
            task.pending_time = None
            task.completed_time = None
            task.results = None
        await session.commit()
        logger.debug("task added/upserted: %s status=%s", task_id, status)
        return task

    async def get(self, session: AsyncSession, task_id: str) -> Task | None:
        return await session.get(Task, task_id)

    async def get_dict(self, session: AsyncSession, task_id: str) -> dict[str, Any] | None:
        task = await self.get(session, task_id)
        return _to_dict(task) if task else None

    async def exists(self, session: AsyncSession, task_id: str) -> bool:
        return await self.get(session, task_id) is not None

    async def update(
        self,
        session: AsyncSession,
        task_id: str,
        *,
        status: str | None = None,
        results: Any | None = None,
    ) -> bool:
        task = await self.get(session, task_id)
        if task is None:
            return False
        if status:
            task.status = status
            if status == READY:
                task.created_time = _now()
                task.results = None
                task.pending_time = None
                task.completed_time = None
            elif status == PENDING:
                task.pending_time = _now()
            elif status == COMPLETED:
                task.completed_time = _now()
        if results is not None:
            task.results = results
        await session.commit()
        return True

    async def list_ids(self, session: AsyncSession) -> list[str]:
        rows = await session.execute(select(Task.id))
        return [row[0] for row in rows.all()]

    async def list(self, session: AsyncSession) -> list[Task]:
        rows = await session.execute(select(Task))
        return list(rows.scalars().all())

    async def remove(self, session: AsyncSession, task_id: str) -> None:
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.commit()

    async def claim_next(
        self,
        session: AsyncSession,
        *,
        client_id: str | None,
    ) -> Task | None:
        """Find and mark as PENDING the next READY task for the given client."""

        stmt = select(Task).where(Task.status == READY).order_by(Task.created_time)
        rows = await session.execute(stmt)
        for task in rows.scalars():
            if not task.client_id or not client_id or task.client_id == client_id:
                task.status = PENDING
                task.pending_time = _now()
                await session.commit()
                return task
        return None

    async def save_history(
        self,
        session: AsyncSession,
        task_id: str,
        results: Any,
        history_days: int = 7,
    ) -> bool:
        task = await self.get(session, task_id)
        if task is None:
            return False
        cutoff = _now() - dt.timedelta(days=max(history_days, 0))
        session.add(
            TaskHistory(
                task_id=task_id,
                results=results,
                created_time=task.created_time,
                pending_time=task.pending_time,
                completed_time=_now(),
            )
        )
        if history_days > 0:
            await session.execute(
                delete(TaskHistory)
                .where(TaskHistory.task_id == task_id)
                .where(TaskHistory.completed_time < cutoff)
            )
        await session.commit()
        return True

    async def history(
        self,
        session: AsyncSession,
        task_id: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]] | None:
        task = await self.get(session, task_id)
        if task is None:
            return None

        start_dt = dt.datetime.fromtimestamp(start_time, dt.timezone.utc) if start_time else None
        end_dt = dt.datetime.fromtimestamp(end_time, dt.timezone.utc) if end_time else None

        stmt = select(TaskHistory).where(TaskHistory.task_id == task_id).order_by(
            TaskHistory.completed_time
        )
        if start_dt is not None:
            stmt = stmt.where(TaskHistory.completed_time >= start_dt)
        if end_dt is not None:
            stmt = stmt.where(TaskHistory.completed_time <= end_dt)

        rows = await session.execute(stmt)
        return [
            {
                "results": h.results,
                "created_time": _iso(h.created_time),
                "pending_time": _iso(h.pending_time),
                "completed_time": _iso(h.completed_time),
            }
            for h in rows.scalars().all()
        ]


task_store = TaskStore()


# --------------------------------------------------------------------------- #
# Sync shims for legacy code paths (APScheduler, threaded triggers/timers).   #
# Internally spin up a private event loop in a background thread so we can    #
# call the async store from sync callbacks without colliding with the main    #
# uvicorn loop.                                                                #
# --------------------------------------------------------------------------- #


class _SyncLoop:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()


_sync_loop: _SyncLoop | None = None
_sync_lock = threading.Lock()


def _get_sync_loop() -> _SyncLoop:
    global _sync_loop
    with _sync_lock:
        if _sync_loop is None:
            _sync_loop = _SyncLoop()
        return _sync_loop


async def _with_session(coro_factory):
    async with AsyncSessionLocal() as session:
        return await coro_factory(session)


class SyncTaskManager:
    """Drop-in replacement for the legacy `task_manager` (sync API)."""

    def add_task(
        self,
        task_id: str,
        client_id: str | None,
        commands: list[str],
        status: str = READY,
        is_chunked: bool = False,
    ) -> None:
        _get_sync_loop().run(
            _with_session(
                lambda s: task_store.add(s, task_id, client_id, commands, status, is_chunked)
            )
        )

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        results: Any | None = None,
    ) -> bool:
        return _get_sync_loop().run(
            _with_session(lambda s: task_store.update(s, task_id, status=status, results=results))
        )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return _get_sync_loop().run(_with_session(lambda s: task_store.get_dict(s, task_id)))

    def remove_task(self, task_id: str) -> None:
        _get_sync_loop().run(_with_session(lambda s: task_store.remove(s, task_id)))

    def task_exists(self, task_id: str) -> bool:
        return _get_sync_loop().run(_with_session(lambda s: task_store.exists(s, task_id)))

    def list_tasks(self) -> list[str]:
        return _get_sync_loop().run(_with_session(lambda s: task_store.list_ids(s)))

    def save_to_history(self, task_id: str, results, history_days: int = 7) -> bool:
        return _get_sync_loop().run(
            _with_session(
                lambda s: task_store.save_history(s, task_id, results, history_days)
            )
        )


sync_task_manager = SyncTaskManager()


# --------------------------------------------------------------------------- #
# One-shot migration from legacy /app/tasks/*.json files.                     #
# --------------------------------------------------------------------------- #


async def migrate_legacy_files(directory: Path | None = None) -> int:
    """If legacy `tasks/<id>.json` files exist, import them into the DB once.

    Idempotent: existing rows in DB are preserved (legacy file wins only when
    DB row is missing).
    """

    directory = directory or settings.legacy_tasks_dir
    if not directory.exists():
        return 0
    imported = 0
    async with AsyncSessionLocal() as session:
        for path in directory.glob("*.json"):
            task_id = path.stem
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                logger.warning("legacy task file unreadable: %s", path)
                continue
            if await task_store.exists(session, task_id):
                continue
            await task_store.add(
                session,
                task_id=task_id,
                client_id=payload.get("client_id"),
                commands=payload.get("commands") or [],
                status=payload.get("status", READY),
                is_chunked=bool(payload.get("chunked", False)),
            )
            if payload.get("results") is not None:
                await task_store.update(session, task_id, results=payload["results"])
            imported += 1
    if imported:
        logger.info("migrated %d legacy task files from %s", imported, directory)
    return imported
