"""/api/nesql — read-only access to imported NESQL data (Phase 2).

NESQL lives in its own SQLite file (see ``kb/04-nesql/schema.md``). We open
it on demand with ``sqlite3`` to avoid coupling SQLAlchemy session config.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

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


@contextmanager
def _open_nesql(required: bool = True) -> Iterator[Optional[sqlite3.Connection]]:
    path = _nesql_path()
    if not path.exists():
        if required:
            raise HTTPException(status_code=404, detail="NESQL database is not imported yet")
        yield None
        return
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _ok(data: Any) -> dict:
    return {"code": 200, "message": "success", "data": data}


# --- meta / status -----------------------------------------------------------


@router.get("/meta", response_model=StandardResponseModel)
async def get_meta() -> dict:
    """Report whether NESQL data is available and per-module counts."""

    path = _nesql_path()
    if not path.exists():
        return _ok({"available": False, "path": str(path), "modules": []})
    with _open_nesql() as conn:
        assert conn is not None
        modules = [
            dict(r)
            for r in conn.execute(
                "SELECT module, row_count, imported_at FROM nesql_import_meta "
                "ORDER BY module"
            ).fetchall()
        ]
        size_bytes = path.stat().st_size
    return _ok({
        "available": True,
        "path": str(path),
        "size_bytes": size_bytes,
        "modules": modules,
    })


# --- items -------------------------------------------------------------------


@router.get("/items", response_model=StandardResponseModel)
async def search_items(
    q: str = Query("", description="Substring on localized_name / unlocal_name"),
    mod_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    with _open_nesql() as conn:
        assert conn is not None
        clauses: list[str] = []
        params: list = []
        if q:
            clauses.append("(localized_name LIKE ? OR unlocal_name LIKE ?)")
            pattern = f"%{q}%"
            params.extend([pattern, pattern])
        if mod_id:
            clauses.append("mod_id = ?")
            params.append(mod_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        total_row = conn.execute(
            f"SELECT COUNT(*) AS c FROM nesql_items {where}", params
        ).fetchone()
        total = int(total_row["c"]) if total_row else 0

        rows = conn.execute(
            f"SELECT id, unlocal_name, localized_name, mod_id, damage, stack_size, nbt_hash "
            f"FROM nesql_items {where} ORDER BY mod_id, unlocal_name "
            f"LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return _ok({
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(r) for r in rows],
    })


@router.get("/items/{item_id}", response_model=StandardResponseModel)
async def get_item(item_id: int) -> dict:
    with _open_nesql() as conn:
        assert conn is not None
        row = conn.execute(
            "SELECT id, unlocal_name, localized_name, mod_id, damage, stack_size, nbt_hash "
            "FROM nesql_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Item not found")
        aspects = conn.execute(
            "SELECT aspect_name, amount FROM nesql_item_aspects WHERE item_id = ?",
            (item_id,),
        ).fetchall()
        ore_names = conn.execute(
            "SELECT o.name FROM nesql_oredict_items oi "
            "JOIN nesql_oredict o ON o.id = oi.ore_id WHERE oi.item_id = ?",
            (item_id,),
        ).fetchall()
    payload = dict(row)
    payload["aspects"] = [dict(a) for a in aspects]
    payload["oredict"] = [r["name"] for r in ore_names]
    return _ok(payload)


# --- mods --------------------------------------------------------------------


@router.get("/mods", response_model=StandardResponseModel)
async def list_mods() -> dict:
    with _open_nesql() as conn:
        assert conn is not None
        rows = conn.execute(
            "SELECT mod_id, COUNT(*) AS items_count FROM nesql_items "
            "WHERE mod_id IS NOT NULL GROUP BY mod_id ORDER BY mod_id"
        ).fetchall()
    return _ok([dict(r) for r in rows])


# --- recipes -----------------------------------------------------------------


def _decode_json(value: Optional[str]) -> Any:
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []


def _nesql_recipe_column_names(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(nesql_recipes)")}


@router.get("/recipes/{recipe_id}", response_model=StandardResponseModel)
async def get_recipe(recipe_id: int) -> dict:
    with _open_nesql() as conn:
        assert conn is not None
        cols = _nesql_recipe_column_names(conn)
        base = "id, recipe_type, duration, eu_per_tick, inputs_json, outputs_json"
        if "recipe_type_label" in cols:
            base = (
                "id, recipe_type, recipe_type_label, duration, eu_per_tick, "
                "inputs_json, outputs_json"
            )
        row = conn.execute(
            f"SELECT {base} FROM nesql_recipes WHERE id = ?",
            (recipe_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
    payload = dict(row)
    payload["inputs"] = _decode_json(payload.pop("inputs_json", None))
    payload["outputs"] = _decode_json(payload.pop("outputs_json", None))
    return _ok(payload)


@router.get("/recipes", response_model=StandardResponseModel)
async def search_recipes(
    output_item_id: Optional[int] = Query(None, description="Filter recipes producing this item"),
    input_item_id: Optional[int] = Query(None, description="Filter recipes consuming this item"),
    recipe_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    join = ""
    clauses: list[str] = []
    params: list = []
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
    with _open_nesql() as conn:
        assert conn is not None
        cols = _nesql_recipe_column_names(conn)
        sel = "r.id, r.recipe_type, r.duration, r.eu_per_tick, r.inputs_json, r.outputs_json"
        if "recipe_type_label" in cols:
            sel = (
                "r.id, r.recipe_type, r.recipe_type_label, r.duration, r.eu_per_tick, "
                "r.inputs_json, r.outputs_json"
            )
        rows = conn.execute(
            f"SELECT DISTINCT {sel} FROM nesql_recipes r {join} {where} "
            f"ORDER BY r.id LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    items = []
    for r in rows:
        payload = dict(r)
        payload["inputs"] = _decode_json(payload.pop("inputs_json", None))
        payload["outputs"] = _decode_json(payload.pop("outputs_json", None))
        items.append(payload)
    return _ok({"limit": limit, "offset": offset, "recipes": items})


# --- quests ------------------------------------------------------------------


@router.get("/quests", response_model=StandardResponseModel)
async def list_quests(
    q: str = Query("", description="Substring filter on quest name"),
    quest_line: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    clauses: list[str] = []
    params: list = []
    if q:
        clauses.append("name LIKE ?")
        params.append(f"%{q}%")
    if quest_line is not None:
        clauses.append("quest_line = ?")
        params.append(quest_line)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with _open_nesql() as conn:
        assert conn is not None
        total = int(conn.execute(
            f"SELECT COUNT(*) AS c FROM nesql_quests {where}", params
        ).fetchone()["c"])
        rows = conn.execute(
            f"SELECT id, name, description, quest_line, parent_id "
            f"FROM nesql_quests {where} ORDER BY quest_line, id "
            f"LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return _ok({
        "total": total,
        "limit": limit,
        "offset": offset,
        "quests": [dict(r) for r in rows],
    })


@router.get("/quests/{quest_id}", response_model=StandardResponseModel)
async def get_quest(quest_id: int) -> dict:
    with _open_nesql() as conn:
        assert conn is not None
        row = conn.execute(
            "SELECT id, name, description, quest_line, parent_id, task_json, reward_json, bq_id "
            "FROM nesql_quests WHERE id = ?",
            (quest_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Quest not found")
        children = conn.execute(
            "SELECT id, name FROM nesql_quests WHERE parent_id = ? ORDER BY id",
            (quest_id,),
        ).fetchall()
    payload = dict(row)
    payload["tasks"] = _decode_json(payload.pop("task_json", None))
    payload["rewards"] = _decode_json(payload.pop("reward_json", None))
    payload["children"] = [dict(c) for c in children]
    return _ok(payload)


# --- oredict -----------------------------------------------------------------


@router.get("/oredict/{name}", response_model=StandardResponseModel)
async def get_oredict_entry(name: str) -> dict:
    with _open_nesql() as conn:
        assert conn is not None
        ore = conn.execute(
            "SELECT id, name FROM nesql_oredict WHERE name = ?", (name,)
        ).fetchone()
        if ore is None:
            raise HTTPException(status_code=404, detail="OreDict entry not found")
        items = conn.execute(
            "SELECT i.id, i.unlocal_name, i.localized_name, i.mod_id "
            "FROM nesql_oredict_items oi "
            "JOIN nesql_items i ON i.id = oi.item_id "
            "WHERE oi.ore_id = ? ORDER BY i.mod_id, i.unlocal_name",
            (ore["id"],),
        ).fetchall()
    payload = dict(ore)
    payload["items"] = [dict(r) for r in items]
    return _ok(payload)
