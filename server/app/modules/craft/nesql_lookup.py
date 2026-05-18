"""Lookup NESQL item names via the read-only NESQL SQLite file."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import app.core.settings as settings_mod


def _nesql_path() -> Path | None:
    url = settings_mod.settings.nesql_database_url
    if not url.startswith("sqlite:///"):
        return None
    p = Path(url.removeprefix("sqlite:///"))
    return p if p.exists() else None


async def nesql_item_id_for_unlocal_name(name: str, damage: int) -> tuple[int, int] | None:
    """Resolve ``(nesql_item_id, damage)`` from exported unlocalized (or localized) name."""

    path = _nesql_path()
    if path is None:
        return None

    def _run() -> tuple[int, int] | None:
        conn = sqlite3.connect(str(path))
        try:
            cur = conn.execute(
                "SELECT id, damage FROM nesql_items WHERE unlocal_name = ? AND damage = ? LIMIT 1",
                (name, damage),
            ).fetchone()
            if cur:
                return int(cur[0]), int(cur[1])
            cur = conn.execute(
                "SELECT id, damage FROM nesql_items WHERE localized_name = ? AND damage = ? LIMIT 1",
                (name, damage),
            ).fetchone()
            if cur:
                return int(cur[0]), int(cur[1])
            return None
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


async def unlocal_name_for_nesql_item(item_id: int) -> str | None:
    path = _nesql_path()
    if path is None:
        return None

    def _run() -> str | None:
        conn = sqlite3.connect(str(path))
        try:
            row = conn.execute(
                "SELECT unlocal_name FROM nesql_items WHERE id = ?",
                (item_id,),
            ).fetchone()
            return str(row[0]) if row else None
        finally:
            conn.close()

    return await asyncio.to_thread(_run)
