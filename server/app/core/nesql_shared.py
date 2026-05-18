"""Single process-wide read-only NESQL sqlite connection (ADR-005 / plan A2).

SQLite connections are not safe for concurrent use from multiple threads even
with ``check_same_thread=False``; all access is serialized with one lock while
still using ``asyncio.to_thread`` so the event loop is not blocked on read I/O.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, Request

import app.core.settings as settings_mod

_NESQL_IO_LOCK = threading.RLock()


def nesql_path_from_settings() -> Path:
    url = settings_mod.settings.nesql_database_url
    if not url.startswith("sqlite:///"):
        raise HTTPException(
            status_code=500, detail="NESQL must be SQLite for this module"
        )
    return Path(url.removeprefix("sqlite:///"))


def open_shared_nesql(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri()
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA query_only = 1")
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA mmap_size = 268435456")
    cur.execute("PRAGMA cache_size = -65536")
    cur.execute("PRAGMA temp_store = MEMORY")
    cur.close()
    return conn


def _has_fts_tables(conn: sqlite3.Connection) -> tuple[bool, bool]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('nesql_items_fts', 'nesql_quests_fts')"
    ).fetchall()
    names = {r[0] for r in rows}
    return ("nesql_items_fts" in names, "nesql_quests_fts" in names)


def _unbind_nesql_core(state: Any) -> None:
    conn = getattr(state, "nesql_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
    state.nesql_conn = None
    state.nesql_path = None
    state.nesql_bound_path = None
    state.nesql_has_fts_items = False
    state.nesql_has_fts_quests = False


def _bind_nesql_core(state: Any, path: Path) -> sqlite3.Connection:
    _unbind_nesql_core(state)
    conn = open_shared_nesql(path)
    state.nesql_conn = conn
    state.nesql_path = path
    state.nesql_bound_path = path.resolve()
    hi, hq = _has_fts_tables(conn)
    state.nesql_has_fts_items = hi
    state.nesql_has_fts_quests = hq
    for k in ("quests_cache_mtime", "quests_tree_data", "quests_lines_data"):
        if hasattr(state, k):
            setattr(state, k, None)
    return conn


def setup_nesql_state(app) -> None:
    """Warm NESQL on startup; re-bound per-request if ``NESQL_DATABASE_URL`` changes."""
    state = app.state
    _unbind_nesql_core(state)
    try:
        path = nesql_path_from_settings()
    except HTTPException:
        return
    if not path.exists():
        return
    with _NESQL_IO_LOCK:
        try:
            _bind_nesql_core(state, path)
        except OSError:
            pass


def teardown_nesql_state(app) -> None:
    with _NESQL_IO_LOCK:
        _unbind_nesql_core(app.state)


def attach_nesql_if_needed(request: Request) -> sqlite3.Connection | None:
    """Ensure ``app.state`` holds a connection for the current ``NESQL_DATABASE_URL``."""
    path = nesql_path_from_settings()
    state = request.app.state
    resolved = path.resolve()
    with _NESQL_IO_LOCK:
        bound = getattr(state, "nesql_bound_path", None)
        conn = getattr(state, "nesql_conn", None)
        if conn is not None and bound == resolved:
            return conn
        if conn is not None:
            _unbind_nesql_core(state)
        if not path.exists():
            return None
        try:
            return _bind_nesql_core(state, path)
        except OSError:
            return None


def require_nesql_conn(request: Request) -> sqlite3.Connection:
    conn = attach_nesql_if_needed(request)
    if conn is None:
        raise HTTPException(
            status_code=404, detail="NESQL database is not imported yet"
        )
    return conn


async def nesql_fetchall(
    conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()
) -> list[sqlite3.Row]:
    def _run() -> list[sqlite3.Row]:
        with _NESQL_IO_LOCK:
            return list(conn.execute(sql, params).fetchall())

    return await asyncio.to_thread(_run)


async def nesql_fetchone(
    conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()
) -> Optional[sqlite3.Row]:
    def _run() -> Optional[sqlite3.Row]:
        with _NESQL_IO_LOCK:
            return conn.execute(sql, params).fetchone()

    return await asyncio.to_thread(_run)


async def nesql_scalar_int(
    conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()
) -> int:
    row = await nesql_fetchone(conn, sql, params)
    if row is None:
        return 0
    v = row[0]
    return int(v) if v is not None else 0
