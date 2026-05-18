"""In-memory quest tree/lines cache keyed by NESQL file mtime (plan A4)."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import Request

from app.core.nesql_shared import attach_nesql_if_needed, nesql_fetchall, nesql_path_from_settings


def init_quest_cache_state(app) -> None:
    app.state.quest_cache_lock = asyncio.Lock()
    app.state.quests_cache_mtime: Optional[float] = None
    app.state.quests_tree_data: Optional[list[dict[str, Any]]] = None
    app.state.quests_lines_data: Optional[list[dict[str, Any]]] = None


def clear_quest_cache(app) -> None:
    st = app.state
    for k in ("quests_cache_mtime", "quests_tree_data", "quests_lines_data"):
        if hasattr(st, k):
            setattr(st, k, None)


def _quest_row_dict(row: Any) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "parent_id": row["parent_id"],
        "quest_line": row["quest_line"],
        "description": row["description"],
        "bq_id": row["bq_id"] if "bq_id" in row.keys() else None,
        "pos_x": row["pos_x"] if "pos_x" in row.keys() else None,
        "pos_y": row["pos_y"] if "pos_y" in row.keys() else None,
        "size_x": row["size_x"] if "size_x" in row.keys() else None,
        "size_y": row["size_y"] if "size_y" in row.keys() else None,
        "icon_item_id": row["icon_item_id"] if "icon_item_id" in row.keys() else None,
    }


async def get_cached_tree_and_lines(
    request: Request,
) -> tuple[Optional[list[dict[str, Any]]], Optional[list[dict[str, Any]]]]:
    state = request.app.state
    if not hasattr(state, "quest_cache_lock"):
        state.quest_cache_lock = asyncio.Lock()
        state.quests_cache_mtime = None
        state.quests_tree_data = None
        state.quests_lines_data = None

    path = nesql_path_from_settings()
    if not path.exists():
        return None, None
    conn = attach_nesql_if_needed(request)
    if conn is None:
        return None, None

    def _mtime() -> float:
        return path.stat().st_mtime

    mtime = await asyncio.to_thread(_mtime)
    lock: asyncio.Lock = state.quest_cache_lock

    if (
        getattr(state, "quests_cache_mtime", None) == mtime
        and state.quests_tree_data is not None
        and state.quests_lines_data is not None
    ):
        return state.quests_tree_data, state.quests_lines_data

    async with lock:
        if (
            getattr(state, "quests_cache_mtime", None) == mtime
            and state.quests_tree_data is not None
            and state.quests_lines_data is not None
        ):
            return state.quests_tree_data, state.quests_lines_data

        rows = await nesql_fetchall(
            conn,
            "SELECT id, name, parent_id, quest_line, description, bq_id, "
            "pos_x, pos_y, size_x, size_y, icon_item_id FROM nesql_quests "
            "ORDER BY quest_line, id",
            (),
        )
        tree = [_quest_row_dict(r) for r in rows]

        line_rows = await nesql_fetchall(
            conn,
            "SELECT id, name, description, quest_line, bq_id FROM nesql_quests "
            "WHERE id < 0 ORDER BY quest_line",
            (),
        )
        lines = [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "quest_line": r["quest_line"],
                "bq_id": r["bq_id"],
            }
            for r in line_rows
        ]

        state.quests_cache_mtime = mtime
        state.quests_tree_data = tree
        state.quests_lines_data = lines
        return tree, lines
