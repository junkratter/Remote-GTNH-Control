"""/api/nesql — read-only access to imported NESQL data (Phase 2).

NESQL lives in a dedicated SQLite file (see ``kb/04-nesql/schema.md``). One
shared read-only connection is opened per process (see ``nesql_shared``).
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth import token_required
from app.core.nesql_redis_cache import (
    get_json,
    item_key,
    recipes_by_output_key,
    set_json,
)
from app.core.nesql_shared import (
    attach_nesql_if_needed,
    nesql_fetchall,
    nesql_fetchone,
    nesql_path_from_settings,
    nesql_scalar_int,
    require_nesql_conn,
)
from app.schemas import StandardResponseModel


router = APIRouter(dependencies=[Depends(token_required)])


def _ok(data: Any) -> dict:
    return {"code": 200, "message": "success", "data": data}


# --- meta / status -----------------------------------------------------------


@router.get("/meta", response_model=StandardResponseModel)
async def get_meta(request: Request) -> dict:
    """Report whether NESQL data is available and per-module counts."""

    path = nesql_path_from_settings()
    if not path.exists():
        return _ok({"available": False, "path": str(path), "modules": []})
    conn = attach_nesql_if_needed(request)
    if conn is None:
        return _ok({"available": False, "path": str(path), "modules": []})

    def _size() -> int:
        return path.stat().st_size

    size_bytes = await asyncio.to_thread(_size)
    rows = await nesql_fetchall(
        conn,
        "SELECT module, row_count, imported_at FROM nesql_import_meta ORDER BY module",
        (),
    )
    modules = [dict(r) for r in rows]
    return _ok({
        "available": True,
        "path": str(path),
        "size_bytes": size_bytes,
        "modules": modules,
    })


# --- items -------------------------------------------------------------------


@router.get("/items", response_model=StandardResponseModel)
async def search_items(
    request: Request,
    q: str = Query("", description="Substring on localized_name / unlocal_name"),
    mod_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    conn = require_nesql_conn(request)
    fts = bool(getattr(request.app.state, "nesql_has_fts_items", False))
    clauses: list[str] = []
    params: list[Any] = []
    if q:
        if fts:
            clauses.append(
                "id IN (SELECT rowid FROM nesql_items_fts WHERE nesql_items_fts MATCH ?)"
            )
            params.append(q)
        else:
            clauses.append("(localized_name LIKE ? OR unlocal_name LIKE ?)")
            pattern = f"%{q}%"
            params.extend([pattern, pattern])
    if mod_id:
        clauses.append("mod_id = ?")
        params.append(mod_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    total = await nesql_scalar_int(
        conn, f"SELECT COUNT(*) AS c FROM nesql_items {where}", tuple(params)
    )

    rows = await nesql_fetchall(
        conn,
        f"SELECT id, unlocal_name, localized_name, mod_id, damage, stack_size, nbt_hash "
        f"FROM nesql_items {where} ORDER BY mod_id, unlocal_name "
        f"LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset),
    )
    return _ok({
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(r) for r in rows],
    })


@router.get("/items/{item_id}", response_model=StandardResponseModel)
async def get_item(
    request: Request,
    item_id: int,
) -> dict:
    conn = require_nesql_conn(request)
    redis = getattr(request.app.state, "redis", None)
    row = await nesql_fetchone(
        conn,
        "SELECT id, unlocal_name, localized_name, mod_id, damage, stack_size, nbt_hash "
        "FROM nesql_items WHERE id = ?",
        (item_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    if redis is not None:
        ck = item_key(str(row["unlocal_name"] or ""), int(row["damage"] or 0))
        cached = await get_json(redis, ck)
        if cached is not None:
            return _ok(cached)

    aspects = await nesql_fetchall(
        conn,
        "SELECT aspect_name, amount FROM nesql_item_aspects WHERE item_id = ?",
        (item_id,),
    )
    ore_names = await nesql_fetchall(
        conn,
        "SELECT o.name FROM nesql_oredict_items oi "
        "JOIN nesql_oredict o ON o.id = oi.ore_id WHERE oi.item_id = ?",
        (item_id,),
    )
    payload = dict(row)
    payload["aspects"] = [dict(a) for a in aspects]
    payload["oredict"] = [r["name"] for r in ore_names]
    if redis is not None:
        await set_json(redis, item_key(str(row["unlocal_name"] or ""), int(row["damage"] or 0)), payload)
    return _ok(payload)


# --- mods --------------------------------------------------------------------


@router.get("/mods", response_model=StandardResponseModel)
async def list_mods(request: Request) -> dict:
    conn = require_nesql_conn(request)
    rows = await nesql_fetchall(
        conn,
        "SELECT mod_id, COUNT(*) AS items_count FROM nesql_items "
        "WHERE mod_id IS NOT NULL GROUP BY mod_id ORDER BY mod_id",
        (),
    )
    return _ok([dict(r) for r in rows])


# --- recipes -----------------------------------------------------------------


def _decode_json(value: Optional[str]) -> Any:
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []


async def _nesql_recipe_column_names(conn: sqlite3.Connection) -> set[str]:
    def _run() -> set[str]:
        return {row[1] for row in conn.execute("PRAGMA table_info(nesql_recipes)")}

    return await asyncio.to_thread(_run)


@router.get("/recipes/{recipe_id}", response_model=StandardResponseModel)
async def get_recipe(request: Request, recipe_id: int) -> dict:
    conn = require_nesql_conn(request)
    cols = await _nesql_recipe_column_names(conn)
    base = "id, recipe_type, duration, eu_per_tick, inputs_json, outputs_json"
    if "recipe_type_label" in cols:
        base = (
            "id, recipe_type, recipe_type_label, duration, eu_per_tick, "
            "inputs_json, outputs_json"
        )
    row = await nesql_fetchone(
        conn,
        f"SELECT {base} FROM nesql_recipes WHERE id = ?",
        (recipe_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    payload = dict(row)
    payload["inputs"] = _decode_json(payload.pop("inputs_json", None))
    payload["outputs"] = _decode_json(payload.pop("outputs_json", None))
    return _ok(payload)


@router.get("/recipes", response_model=StandardResponseModel)
async def search_recipes(
    request: Request,
    output_item_id: Optional[int] = Query(None, description="Filter recipes producing this item"),
    input_item_id: Optional[int] = Query(None, description="Filter recipes consuming this item"),
    recipe_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    join = ""
    clauses: list[str] = []
    params: list[Any] = []
    redis = getattr(request.app.state, "redis", None)
    if output_item_id is not None:
        join += (
            " JOIN nesql_recipe_outputs ro ON ro.recipe_id = r.id "
            "AND ro.item_id = ?"
        )
        params.append(output_item_id)
    if input_item_id is not None:
        join += (
            " JOIN nesql_recipe_inputs ri ON ri.recipe_id = r.id "
            "AND ri.item_id = ?"
        )
        params.append(input_item_id)
    if recipe_type:
        clauses.append("r.recipe_type = ?")
        params.append(recipe_type)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = require_nesql_conn(request)
    if redis is not None and output_item_id is not None:
        rk = recipes_by_output_key(
            output_item_id=output_item_id,
            input_item_id=input_item_id,
            recipe_type=recipe_type,
            limit=limit,
            offset=offset,
        )
        cached = await get_json(redis, rk)
        if cached is not None:
            return _ok(cached)

    cols = await _nesql_recipe_column_names(conn)
    sel = "r.id, r.recipe_type, r.duration, r.eu_per_tick, r.inputs_json, r.outputs_json"
    if "recipe_type_label" in cols:
        sel = (
            "r.id, r.recipe_type, r.recipe_type_label, r.duration, r.eu_per_tick, "
            "r.inputs_json, r.outputs_json"
        )
    rows = await nesql_fetchall(
        conn,
        f"SELECT DISTINCT {sel} FROM nesql_recipes r {join} {where} "
        f"ORDER BY r.id LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset),
    )
    items = []
    for r in rows:
        payload = dict(r)
        payload["inputs"] = _decode_json(payload.pop("inputs_json", None))
        payload["outputs"] = _decode_json(payload.pop("outputs_json", None))
        items.append(payload)
    out = {"limit": limit, "offset": offset, "recipes": items}
    if redis is not None and output_item_id is not None:
        await set_json(
            redis,
            recipes_by_output_key(
                output_item_id=output_item_id,
                input_item_id=input_item_id,
                recipe_type=recipe_type,
                limit=limit,
                offset=offset,
            ),
            out,
        )
    return _ok(out)


# --- quests ------------------------------------------------------------------


@router.get("/quests", response_model=StandardResponseModel)
async def list_quests(
    request: Request,
    q: str = Query("", description="Substring filter on quest name"),
    quest_line: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    clauses: list[str] = []
    params: list[Any] = []
    if q:
        fts_q = bool(getattr(request.app.state, "nesql_has_fts_quests", False))
        if fts_q:
            clauses.append(
                "id IN (SELECT rowid FROM nesql_quests_fts WHERE nesql_quests_fts MATCH ?)"
            )
            params.append(q)
        else:
            clauses.append("name LIKE ?")
            params.append(f"%{q}%")
    if quest_line is not None:
        clauses.append("quest_line = ?")
        params.append(quest_line)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = require_nesql_conn(request)
    total = await nesql_scalar_int(
        conn, f"SELECT COUNT(*) AS c FROM nesql_quests {where}", tuple(params)
    )
    rows = await nesql_fetchall(
        conn,
        f"SELECT id, name, description, quest_line, parent_id "
        f"FROM nesql_quests {where} ORDER BY quest_line, id "
        f"LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset),
    )
    return _ok({
        "total": total,
        "limit": limit,
        "offset": offset,
        "quests": [dict(r) for r in rows],
    })


@router.get("/quests/{quest_id}", response_model=StandardResponseModel)
async def get_quest(request: Request, quest_id: int) -> dict:
    conn = require_nesql_conn(request)
    row = await nesql_fetchone(
        conn,
        "SELECT id, name, description, quest_line, parent_id, task_json, reward_json, bq_id "
        "FROM nesql_quests WHERE id = ?",
        (quest_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Quest not found")
    children = await nesql_fetchall(
        conn,
        "SELECT id, name FROM nesql_quests WHERE parent_id = ? ORDER BY id",
        (quest_id,),
    )
    payload = dict(row)
    payload["tasks"] = _decode_json(payload.pop("task_json", None))
    payload["rewards"] = _decode_json(payload.pop("reward_json", None))
    payload["children"] = [dict(c) for c in children]
    return _ok(payload)


# --- oredict -----------------------------------------------------------------


@router.get("/oredict/{name}", response_model=StandardResponseModel)
async def get_oredict_entry(request: Request, name: str) -> dict:
    conn = require_nesql_conn(request)
    ore = await nesql_fetchone(
        conn,
        "SELECT id, name FROM nesql_oredict WHERE name = ?",
        (name,),
    )
    if ore is None:
        raise HTTPException(status_code=404, detail="OreDict entry not found")
    items = await nesql_fetchall(
        conn,
        "SELECT i.id, i.unlocal_name, i.localized_name, i.mod_id "
        "FROM nesql_oredict_items oi "
        "JOIN nesql_items i ON i.id = oi.item_id "
        "WHERE oi.ore_id = ? ORDER BY i.mod_id, i.unlocal_name",
        (ore["id"],),
    )
    payload = dict(ore)
    payload["items"] = [dict(r) for r in items]
    return _ok(payload)
