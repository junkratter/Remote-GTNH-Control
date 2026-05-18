"""build_resolved → ``craft_recipes_resolved`` graph (plan C2)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import CraftRecipeInput, CraftRecipeOutput, CraftRecipeResolved
from app.modules.craft.build_resolved import build


def _minimal_nesql(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE nesql_items (
                id INTEGER PRIMARY KEY,
                unlocal_name TEXT,
                localized_name TEXT,
                mod_id TEXT,
                damage INTEGER,
                stack_size INTEGER,
                nbt_hash TEXT
            );
            CREATE TABLE nesql_recipes (
                id INTEGER PRIMARY KEY,
                recipe_type TEXT,
                duration INTEGER,
                eu_per_tick INTEGER,
                inputs_json TEXT,
                outputs_json TEXT
            );
            CREATE TABLE nesql_oredict (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            );
            CREATE TABLE nesql_oredict_items (
                ore_id INTEGER,
                item_id INTEGER,
                PRIMARY KEY (ore_id, item_id)
            );
            INSERT INTO nesql_items (id, unlocal_name, damage) VALUES (10, 'dustIron', 0);
            INSERT INTO nesql_items (id, unlocal_name, damage) VALUES (20, 'ingotIron', 0);
            """
        )
        inputs = json.dumps(
            [{"item_id": 10, "slot": 0, "amount": 2, "required": True}]
        )
        outputs = json.dumps([{"item_id": 20, "slot": 0, "amount": 1, "chance": 1_000_000}])
        conn.execute(
            "INSERT INTO nesql_recipes (id, recipe_type, duration, eu_per_tick, inputs_json, outputs_json) "
            "VALUES (99, 'ELECTRIC_FURNACE', 100, 2, ?, ?)",
            (inputs, outputs),
        )
        conn.commit()
    finally:
        conn.close()


def test_build_resolved_inserts_one_recipe(tmp_path: Path) -> None:
    main_sqlite = tmp_path / "main.sqlite"
    engine = create_engine(f"sqlite:///{main_sqlite}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)

    nesql = tmp_path / "nesql.sqlite"
    _minimal_nesql(nesql)

    with factory() as session:
        recipes, edges = build(session, str(nesql))

    assert recipes == 1
    assert edges == 2

    with factory() as session:
        resolved = session.execute(select(CraftRecipeResolved)).scalars().all()
        ins = session.execute(select(CraftRecipeInput)).scalars().all()
        outs = session.execute(select(CraftRecipeOutput)).scalars().all()
    assert len(resolved) == 1
    assert resolved[0].nesql_recipe_id == 99
    assert len(ins) == 1 and len(outs) == 1
    assert ins[0].amount == 2
    assert outs[0].amount == 1
