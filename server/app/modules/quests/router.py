"""/api/quests — BetterQuesting tree from NESQL (Phase 6).

The quest tree file path follows ``NESQL_DATABASE_URL``. Tree and lines
responses are cached in memory and invalidated when the file mtime changes
(plan A4). Other routes use the shared NESQL connection and ``asyncio.to_thread``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth import token_required
from app.core.nesql_shared import (
    nesql_fetchall,
    nesql_fetchone,
    nesql_path_from_settings,
    nesql_scalar_int,
    require_nesql_conn,
)
from app.core.quest_cache import get_cached_tree_and_lines
from app.schemas import StandardResponseModel


router = APIRouter(dependencies=[Depends(token_required)])


@router.get("/tree", response_model=StandardResponseModel)
async def quest_tree(request: Request) -> dict:
    """Return whole quest tree as a flat list (frontend builds tree client-side)."""

    out, _ = await get_cached_tree_and_lines(request)
    if out is None:
        return {"code": 200, "message": "NESQL not imported yet", "data": []}
    return {"code": 200, "message": "success", "data": out}


@router.get("/lines", response_model=StandardResponseModel)
async def quest_lines(request: Request) -> dict:
    """Quest book chapters (negative root ids)."""

    _, out = await get_cached_tree_and_lines(request)
    if out is None:
        return {"code": 200, "message": "NESQL not imported yet", "data": []}
    return {"code": 200, "message": "success", "data": out}


@router.get("/board", response_model=StandardResponseModel)
async def quest_board(
    request: Request,
    line_root_id: int = Query(..., description="Negative id of quest line root, e.g. -3"),
) -> dict:
    """Better Questing-style board: positioned nodes and prerequisite edges."""

    if line_root_id >= 0:
        raise HTTPException(status_code=400, detail="line_root_id must be negative")

    path = nesql_path_from_settings()
    if not path.exists():
        return {"code": 200, "message": "NESQL not imported yet", "data": None}

    conn = require_nesql_conn(request)
    line_no = -line_root_id

    line = await nesql_fetchone(
        conn,
        "SELECT id, name, description, quest_line, bq_id FROM nesql_quests WHERE id = ?",
        (line_root_id,),
    )
    if line is None:
        raise HTTPException(status_code=404, detail="Quest line not found")

    quests = await nesql_fetchall(
        conn,
        "SELECT id, name, description, bq_id, pos_x, pos_y, size_x, size_y, icon_item_id "
        "FROM nesql_quests WHERE quest_line = ? AND id > 0 "
        "ORDER BY COALESCE(pos_y, 99999), COALESCE(pos_x, 99999), id",
        (line_no,),
    )
    quest_ids = [r["id"] for r in quests]
    edges: list[dict] = []
    if quest_ids:
        placeholders = ",".join("?" * len(quest_ids))
        edge_rows = await nesql_fetchall(
            conn,
            f"SELECT from_quest_id, to_quest_id FROM nesql_quest_edges "
            f"WHERE from_quest_id IN ({placeholders}) AND to_quest_id IN ({placeholders})",
            tuple(quest_ids) + tuple(quest_ids),
        )
        edges = [{"from": r[0], "to": r[1]} for r in edge_rows]

    total = await nesql_scalar_int(
        conn,
        "SELECT COUNT(*) FROM nesql_quests WHERE quest_line = ? AND id > 0",
        (line_no,),
    )
    with_pos = sum(
        1 for r in quests if r["pos_x"] is not None and r["pos_y"] is not None
    )

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
async def quest_search(
    request: Request,
    q: str = Query(..., min_length=2),
    limit: int = 50,
) -> dict:
    path = nesql_path_from_settings()
    if not path.exists():
        return {"code": 200, "message": "NESQL not imported yet", "data": []}

    conn = require_nesql_conn(request)
    fts = bool(getattr(request.app.state, "nesql_has_fts_quests", False))
    if fts:
        rows = await nesql_fetchall(
            conn,
            "SELECT id, name, parent_id, quest_line FROM nesql_quests "
            "WHERE id IN (SELECT rowid FROM nesql_quests_fts WHERE nesql_quests_fts MATCH ?) "
            "LIMIT ?",
            (q, limit),
        )
    else:
        pattern = f"%{q}%"
        rows = await nesql_fetchall(
            conn,
            "SELECT id, name, parent_id, quest_line FROM nesql_quests "
            "WHERE name LIKE ? OR description LIKE ? LIMIT ?",
            (pattern, pattern, limit),
        )
    out = [
        {"id": r["id"], "name": r["name"], "parent_id": r["parent_id"], "quest_line": r["quest_line"]}
        for r in rows
    ]
    return {"code": 200, "message": "success", "data": out}
