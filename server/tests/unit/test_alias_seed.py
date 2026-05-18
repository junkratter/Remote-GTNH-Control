"""Craft alias seeding from NESQL OreDict (plan C1)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import CraftAlias, CraftAliasMember
from app.modules.craft.seed_aliases import seed_from_nesql


def test_seed_from_nesql_creates_ingot_iron_alias(tmp_path: Path) -> None:
    main_sqlite = tmp_path / "main.sqlite"
    engine = create_engine(f"sqlite:///{main_sqlite}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)

    nesql_path = tmp_path / "nesql.sqlite"
    conn = sqlite3.connect(nesql_path)
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
            CREATE TABLE nesql_oredict (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            );
            CREATE TABLE nesql_oredict_items (
                ore_id INTEGER,
                item_id INTEGER,
                PRIMARY KEY (ore_id, item_id)
            );
            INSERT INTO nesql_oredict (id, name) VALUES (1, 'ingotIron');
            INSERT INTO nesql_items (id, unlocal_name, damage)
            VALUES (100, 'ingotIron', 0);
            INSERT INTO nesql_oredict_items (ore_id, item_id) VALUES (1, 100);
            """
        )
        conn.commit()
    finally:
        conn.close()

    with factory() as session:
        touched = seed_from_nesql(session, str(nesql_path))
    assert touched == 1

    with factory() as session:
        alias = session.execute(
            select(CraftAlias).where(CraftAlias.key == "ingotIron")
        ).scalar_one()
        members = (
            session.execute(
                select(CraftAliasMember).where(CraftAliasMember.alias_id == alias.id)
            )
            .scalars()
            .all()
        )
    assert len(members) == 1
    assert members[0].nesql_item_id == 100
    assert members[0].damage == 0
