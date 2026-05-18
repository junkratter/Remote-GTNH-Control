"""/api/quests — BetterQuesting tree from NESQL (Phase 6).

The actual quest tree lives in the NESQL SQLite (separate file from the
main app DB). The endpoints here are thin readers; the import job is
`tools/nesql-import/`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import token_required
from app.core.settings import settings
from app.schemas import StandardResponseModel


router = APIRouter(dependencies=[Depends(token_required)])


def _nesql_path() -> Path:
    url = settings.nesql_database_url
    if not url.startswith("sqlite:///"):
        raise HTTPException(status_code=500, detail="NESQL must be SQLite for this module")
    return Path(url.removeprefix("sqlite:///"))


def _quest_row_dict(row: sqlite3.Row) -> dict:
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


@router.get("/tree", response_model=StandardResponseModel)
async def quest_tree() -> dict:
    """Return whole quest tree as a flat list (frontend builds tree client-side)."""

    import sqlite3

    db_path = _nesql_path()
    if not db_path.exists():
        return {"code": 200, "message": "NESQL not imported yet", "data": []}

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, parent_id, quest_line, description, bq_id, "
            "pos_x, pos_y, size_x, size_y, icon_item_id FROM nesql_quests "
            "ORDER BY quest_line, id"
        ).fetchall()
    out = [_quest_row_dict(r) for r in rows]
    return {"code": 200, "message": "success", "data": out}


@router.get("/lines", response_model=StandardResponseModel)
async def quest_lines() -> dict:
    """Quest book chapters (negative root ids)."""

    import sqlite3

    db_path = _nesql_path()
    if not db_path.exists():
        return {"code": 200, "message": "NESQL not imported yet", "data": []}

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, description, quest_line, bq_id FROM nesql_quests "
            "WHERE id < 0 ORDER BY quest_line"
        ).fetchall()
    out = [
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "quest_line": r["quest_line"],
            "bq_id": r["bq_id"],
        }
        for r in rows
    ]
    return {"code": 200, "message": "success", "data": out}


@router.get("/board", response_model=StandardResponseModel)
async def quest_board(
    line_root_id: int = Query(..., description="Negative id of quest line root, e.g. -3"),
) -> dict:
    """Better Questing-style board: positioned nodes and prerequisite edges."""

    import sqlite3

    if line_root_id >= 0:
        raise HTTPException(status_code=400, detail="line_root_id must be negative")

    db_path = _nesql_path()
    if not db_path.exists():
        return {"code": 200, "message": "NESQL not imported yet", "data": None}

    line_no = -line_root_id
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        line = conn.execute(
            "SELECT id, name, description, quest_line, bq_id FROM nesql_quests WHERE id = ?",
            (line_root_id,),
        ).fetchone()
        if line is None:
            raise HTTPException(status_code=404, detail="Quest line not found")

        quests = conn.execute(
            "SELECT id, name, description, bq_id, pos_x, pos_y, size_x, size_y, icon_item_id "
            "FROM nesql_quests WHERE quest_line = ? AND id > 0 "
            "ORDER BY COALESCE(pos_y, 99999), COALESCE(pos_x, 99999), id",
            (line_no,),
        ).fetchall()
        quest_ids = [r["id"] for r in quests]
        edges: list[dict] = []
        if quest_ids:
            placeholders = ",".join("?" * len(quest_ids))
            edge_rows = conn.execute(
                f"SELECT from_quest_id, to_quest_id FROM nesql_quest_edges "
                f"WHERE from_quest_id IN ({placeholders}) AND to_quest_id IN ({placeholders})",
                quest_ids + quest_ids,
            ).fetchall()
            edges = [
                {"from": r[0], "to": r[1]}
                for r in edge_rows
            ]

        total = conn.execute(
            "SELECT COUNT(*) FROM nesql_quests WHERE quest_line = ? AND id > 0",
            (line_no,),
        ).fetchone()[0]
        with_pos = sum(1 for r in quests if r["pos_x"] is not None and r["pos_y"] is not None)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "line": dict(line),
            "quests": [dict(r) for r in quests],
            "edges": edges,
            "completion": {"done": 0, "total": total, "placed": with_pos},
            "layout": "bq" if with_pos >= max(1, len(quests) // 2) else "auto",
        },
    }


@router.get("/search", response_model=StandardResponseModel)
async def quest_search(q: str = Query(..., min_length=2), limit: int = 50) -> dict:
    import sqlite3

    db_path = _nesql_path()
    if not db_path.exists():
        return {"code": 200, "message": "NESQL not imported yet", "data": []}

    pattern = f"%{q}%"
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, parent_id, quest_line FROM nesql_quests "
            "WHERE name LIKE ? OR description LIKE ? LIMIT ?",
            (pattern, pattern, limit),
        ).fetchall()
    out = [
        {"id": r[0], "name": r[1], "parent_id": r[2], "quest_line": r[3]}
        for r in rows
    ]
    return {"code": 200, "message": "success", "data": out}
