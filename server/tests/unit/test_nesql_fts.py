"""FTS5 search paths when virtual tables exist (plan A3)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client_fts_db():
    tmp = tempfile.mkdtemp()
    nesql = Path(tmp) / "n.sqlite"
    main = Path(tmp) / "m.sqlite"
    for p in (nesql, main):
        if p.exists():
            p.unlink()
    conn = sqlite3.connect(nesql)
    conn.executescript(
        """
        CREATE TABLE nesql_items (
            id INTEGER PRIMARY KEY, unlocal_name TEXT, localized_name TEXT,
            mod_id TEXT, damage INTEGER, stack_size INTEGER, nbt_hash TEXT
        );
        INSERT INTO nesql_items VALUES
            (1, 'item.ingotIron', 'Iron Ingot', 'minecraft', 0, 64, NULL),
            (2, 'item.ingotGold', 'Gold Ingot', 'minecraft', 0, 64, NULL);
        CREATE VIRTUAL TABLE nesql_items_fts USING fts5(
            localized_name, unlocal_name,
            content='nesql_items', content_rowid='id', tokenize='unicode61'
        );
        INSERT INTO nesql_items_fts(rowid, localized_name, unlocal_name)
            SELECT id, localized_name, unlocal_name FROM nesql_items;

        CREATE TABLE nesql_quests (
            id INTEGER PRIMARY KEY, name TEXT, description TEXT,
            quest_line INTEGER, parent_id INTEGER, task_json TEXT, reward_json TEXT,
            bq_id TEXT, pos_x INTEGER, pos_y INTEGER, size_x INTEGER, size_y INTEGER,
            icon_item_id INTEGER
        );
        INSERT INTO nesql_quests VALUES
            (-1, 'Line', '', 1, NULL, '[]', '[]', 'l1', NULL,NULL,NULL,NULL,NULL),
            (1, 'Pickup iron', 'Get iron ingots', 1, -1, '[]', '[]', 'q1', NULL,NULL,NULL,NULL,NULL);
        CREATE VIRTUAL TABLE nesql_quests_fts USING fts5(
            name, description,
            content='nesql_quests', content_rowid='id', tokenize='unicode61'
        );
        INSERT INTO nesql_quests_fts(rowid, name, description)
            SELECT id, name, description FROM nesql_quests;

        CREATE TABLE nesql_import_meta (
            module TEXT PRIMARY KEY, row_count INTEGER, imported_at TEXT
        );
        INSERT INTO nesql_import_meta VALUES ('items', 2, '2026-01-01');
        CREATE TABLE nesql_fluids (id INTEGER PRIMARY KEY);
        CREATE TABLE nesql_recipes (id INTEGER PRIMARY KEY);
        CREATE TABLE nesql_recipe_inputs (recipe_id INTEGER);
        CREATE TABLE nesql_recipe_outputs (recipe_id INTEGER);
        CREATE TABLE nesql_oredict (id INTEGER PRIMARY KEY);
        CREATE TABLE nesql_oredict_items (ore_id INTEGER);
        CREATE TABLE nesql_item_aspects (item_id INTEGER);
        CREATE TABLE nesql_quest_edges (from_quest_id INTEGER, to_quest_id INTEGER);
        """
    )
    conn.commit()
    conn.close()

    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{main}"
    os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{main}"
    os.environ["NESQL_DATABASE_URL"] = f"sqlite:///{nesql}"

    import app.core.settings as settings_mod

    settings_mod.settings = settings_mod.Settings()

    from app.db.base import Base
    from app.main import create_app
    from app.db.session import engine as app_engine

    application = create_app()
    async with app_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
        headers={"X-Server-Token": "test-token"},
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_items_fts_match_iron_ingot(client_fts_db):
    r = await client_fts_db.get("/api/nesql/items", params={"q": "iron"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("data") is not None, body
    data = body["data"]
    assert data["total"] >= 1
    names = {x["localized_name"] for x in data["items"]}
    assert "Iron Ingot" in names


@pytest.mark.asyncio
async def test_quest_search_fts(client_fts_db):
    r = await client_fts_db.get("/api/quests/search", params={"q": "Pickup"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data is not None
    assert len(data) >= 1
