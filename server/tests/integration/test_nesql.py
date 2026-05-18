"""Smoke tests for /api/nesql/* and /api/quests/*.

We don't require a real HSQLDB dump; instead the test builds a small
fixture SQLite that mimics the schema produced by
``tools/nesql-import/import.py``.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


SCHEMA = """
CREATE TABLE nesql_items (
    id INTEGER PRIMARY KEY,
    unlocal_name TEXT,
    localized_name TEXT,
    mod_id TEXT,
    damage INTEGER,
    stack_size INTEGER,
    nbt_hash TEXT
);
CREATE TABLE nesql_fluids (
    id INTEGER PRIMARY KEY, internal_name TEXT, localized_name TEXT, mod_id TEXT
);
CREATE TABLE nesql_recipes (
    id INTEGER PRIMARY KEY, recipe_type TEXT, duration INTEGER,
    eu_per_tick INTEGER, inputs_json TEXT DEFAULT '[]', outputs_json TEXT DEFAULT '[]',
    recipe_type_label TEXT
);
CREATE TABLE nesql_recipe_inputs (
    recipe_id INTEGER, slot INTEGER, item_id INTEGER, fluid_id INTEGER, amount INTEGER,
    PRIMARY KEY (recipe_id, slot, item_id, fluid_id)
);
CREATE TABLE nesql_recipe_outputs (
    recipe_id INTEGER, slot INTEGER, item_id INTEGER, fluid_id INTEGER,
    amount INTEGER, chance INTEGER,
    PRIMARY KEY (recipe_id, slot, item_id, fluid_id)
);
CREATE TABLE nesql_oredict (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
CREATE TABLE nesql_oredict_items (
    ore_id INTEGER, item_id INTEGER, PRIMARY KEY (ore_id, item_id)
);
CREATE TABLE nesql_item_aspects (
    item_id INTEGER, aspect_name TEXT, amount INTEGER,
    PRIMARY KEY (item_id, aspect_name)
);
CREATE TABLE nesql_quests (
    id INTEGER PRIMARY KEY, name TEXT, description TEXT,
    quest_line INTEGER, parent_id INTEGER, task_json TEXT, reward_json TEXT,
    bq_id TEXT, pos_x INTEGER, pos_y INTEGER, size_x INTEGER, size_y INTEGER,
    icon_item_id INTEGER
);
CREATE TABLE nesql_quest_edges (
    from_quest_id INTEGER NOT NULL, to_quest_id INTEGER NOT NULL,
    PRIMARY KEY (from_quest_id, to_quest_id)
);
CREATE TABLE nesql_import_meta (
    module TEXT PRIMARY KEY, row_count INTEGER, imported_at TEXT
);
"""


@pytest.fixture(scope="module")
def nesql_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("nesql") / "nesql.sqlite"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO nesql_items VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "item.IngotIron", "Iron Ingot", "minecraft", 0, 64, None),
            (2, "tile.gt.blockmachines", "Electric Furnace", "gregtech", 0, 64, "abc"),
        ],
    )
    conn.executemany(
        "INSERT INTO nesql_recipes (id, recipe_type, duration, eu_per_tick, recipe_type_label) VALUES (?, ?, ?, ?, ?)",
        [
            (10, "minecraft.crafting", 0, 0, "Crafting Table"),
            (11, "gregtech.alloy_smelter", 200, 8, "Alloy Smelter"),
        ],
    )
    conn.executemany(
        "INSERT INTO nesql_recipe_inputs VALUES (?, ?, ?, ?, ?)",
        [(10, 0, 1, None, 1), (11, 0, 1, None, 2)],
    )
    conn.executemany(
        "INSERT INTO nesql_recipe_outputs VALUES (?, ?, ?, ?, ?, ?)",
        [(10, 0, 2, None, 1, 10000), (11, 0, 2, None, 1, 10000)],
    )
    # materialise JSON
    conn.execute(
        "UPDATE nesql_recipes SET inputs_json='[{\"slot\":0,\"item_id\":1,\"fluid_id\":null,\"amount\":1}]', "
        "outputs_json='[{\"slot\":0,\"item_id\":2,\"fluid_id\":null,\"amount\":1,\"chance\":10000}]' WHERE id IN (10,11)"
    )
    conn.executemany(
        "INSERT INTO nesql_oredict VALUES (?, ?)", [(100, "ingotIron"), (101, "blockMachine")]
    )
    conn.executemany(
        "INSERT INTO nesql_oredict_items VALUES (?, ?)", [(100, 1), (101, 2)]
    )
    conn.executemany(
        "INSERT INTO nesql_item_aspects VALUES (?, ?, ?)",
        [(1, "Metallum", 4), (1, "Terra", 1)],
    )
    conn.executemany(
        "INSERT INTO nesql_quests "
        "(id, name, description, quest_line, parent_id, task_json, reward_json, "
        "bq_id, pos_x, pos_y, size_x, size_y, icon_item_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (-1, "Chapter", "Line desc", 1, None, "[]", "[]", "lineA", None, None, None, None, None),
            (1, "Welcome", "Pickup iron", 1, -1, "[]", "[]", "qA", 10, 20, 24, 24, 1),
            (2, "Smelting", "Make iron", 1, -1, "[]", "[]", "qB", 80, 20, 24, 24, None),
        ],
    )
    conn.executemany(
        "INSERT INTO nesql_quest_edges VALUES (?, ?)",
        [(1, 2)],
    )
    conn.executemany(
        "INSERT INTO nesql_import_meta VALUES (?, ?, '2026-05-16')",
        [("items", 2), ("recipes", 2), ("quests", 2)],
    )
    conn.commit()
    conn.close()

    from app.core.settings import settings

    old_url = settings.nesql_database_url
    # Mutate the singleton in place so existing imports keep their reference.
    object.__setattr__(settings, "nesql_database_url", f"sqlite:///{db_path}")

    yield db_path

    object.__setattr__(settings, "nesql_database_url", old_url)


@pytest.mark.asyncio
async def test_nesql_meta(client, nesql_db):
    resp = await client.get("/api/nesql/meta")
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["available"] is True
    modules = {m["module"]: m["row_count"] for m in body["data"]["modules"]}
    assert modules["items"] == 2


@pytest.mark.asyncio
async def test_nesql_items_search(client, nesql_db):
    resp = await client.get("/api/nesql/items", params={"q": "iron"})
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["localized_name"] == "Iron Ingot"


@pytest.mark.asyncio
async def test_nesql_item_detail(client, nesql_db):
    resp = await client.get("/api/nesql/items/1")
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["unlocal_name"] == "item.IngotIron"
    assert any(a["aspect_name"] == "Metallum" for a in body["data"]["aspects"])
    assert "ingotIron" in body["data"]["oredict"]


@pytest.mark.asyncio
async def test_nesql_recipes_by_output(client, nesql_db):
    resp = await client.get("/api/nesql/recipes", params={"output_item_id": 2})
    body = resp.json()
    assert body["code"] == 200
    assert len(body["data"]["recipes"]) == 2
    assert all(r["outputs"][0]["item_id"] == 2 for r in body["data"]["recipes"])


@pytest.mark.asyncio
async def test_nesql_quests_list_and_detail(client, nesql_db):
    listing = await client.get("/api/nesql/quests", params={"q": "Smelt"})
    body = listing.json()
    assert body["code"] == 200
    assert body["data"]["total"] == 1

    detail = await client.get("/api/nesql/quests/1")
    body = detail.json()
    assert body["code"] == 200
    assert body["data"]["name"] == "Welcome"
    assert body["data"]["bq_id"] == "qA"


@pytest.mark.asyncio
async def test_api_quests_tree_flat_list(client, nesql_db):
    """Phase 6: /api/quests/tree reads the same NESQL SQLite as Wiki."""
    resp = await client.get("/api/quests/tree")
    body = resp.json()
    assert body["code"] == 200
    rows = body["data"]
    assert isinstance(rows, list)
    assert len(rows) == 3
    ids = {r["id"] for r in rows}
    assert ids == {-1, 1, 2}
    by_id = {r["id"]: r for r in rows}
    assert by_id[1]["parent_id"] == -1
    assert by_id[2]["parent_id"] == -1


@pytest.mark.asyncio
async def test_api_quests_board(client, nesql_db):
    resp = await client.get("/api/quests/board", params={"line_root_id": -1})
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["line"]["id"] == -1
    assert len(data["quests"]) == 2
    assert len(data["edges"]) == 1
    assert data["edges"][0] == {"from": 1, "to": 2}


@pytest.mark.asyncio
async def test_api_quests_search(client, nesql_db):
    resp = await client.get("/api/quests/search", params={"q": "iron"})
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)
    # Matches name or description (NESQL fixture: Welcome / Pickup iron).
    assert len(body["data"]) >= 1
    assert any(r["id"] == 1 for r in body["data"])
