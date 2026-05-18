"""Bootstrap ``craft_aliases`` / ``craft_alias_members`` from NESQL OreDict.

Run after ``tools/nesql-import/import.py``::

    cd server && PYTHONPATH=. python -m app.modules.craft.seed_aliases \\
        --nesql /path/to/nesql.sqlite

Requires ``SYNC_DATABASE_URL`` (SQLAlchemy sync URL for the main DB), e.g.::

    export SYNC_DATABASE_URL=sqlite:////abs/path/to/remote-gtnh-control.sqlite
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import CraftAlias, CraftAliasMember


def _load_oredict_groups(nesql_path: str) -> dict[str, list[tuple[int, int]]]:
    """Map OreDict name -> [(nesql_item_id, damage), ...]."""

    conn = sqlite3.connect(nesql_path)
    try:
        rows = conn.execute(
            """
            SELECT o.name, i.id AS item_id, i.damage
            FROM nesql_oredict o
            JOIN nesql_oredict_items oi ON o.id = oi.ore_id
            JOIN nesql_items i ON i.id = oi.item_id
            """
        ).fetchall()
    finally:
        conn.close()

    groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for name, item_id, damage in rows:
        groups[str(name)].append((int(item_id), int(damage or 0)))
    return groups


def seed_from_nesql(session: Session, nesql_path: str) -> int:
    """Idempotent refresh of oredict-backed aliases. Returns number of groups."""

    groups = _load_oredict_groups(nesql_path)
    touched = 0
    for name, members in sorted(groups.items()):
        row = session.execute(select(CraftAlias).where(CraftAlias.key == name)).scalar_one_or_none()
        if row is None:
            row = CraftAlias(key=name, source="oredict", priority=0)
            session.add(row)
            session.flush()
        else:
            row.source = "oredict"
            session.execute(delete(CraftAliasMember).where(CraftAliasMember.alias_id == row.id))
        for item_id, damage in members:
            session.add(
                CraftAliasMember(
                    alias_id=row.id,
                    nesql_item_id=item_id,
                    damage=damage,
                    weight=1,
                    preferred=False,
                )
            )
        touched += 1
    session.commit()
    return touched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nesql", required=True, help="Path to nesql.sqlite")
    args = parser.parse_args(argv)

    url = os.environ.get("SYNC_DATABASE_URL")
    if not url:
        print("SYNC_DATABASE_URL is required", file=sys.stderr)
        return 1
    if not os.path.isfile(args.nesql):
        print("NESQL file not found:", args.nesql, file=sys.stderr)
        return 1

    engine = create_engine(url, future=True)
    S = sessionmaker(engine, future=True)
    with S() as session:
        n = seed_from_nesql(session, args.nesql)
        print(f"seed_aliases: updated {n} OreDict groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
