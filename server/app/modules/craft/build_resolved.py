"""Rebuild ``craft_recipes_resolved`` + inputs/outputs from NESQL.

Run after ``seed_aliases`` (OreDict groups must exist for oredict items)::

    cd server && PYTHONPATH=. python -m app.modules.craft.build_resolved --nesql /path/to/nesql.sqlite

Uses ``SYNC_DATABASE_URL`` for the main database.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sqlite3
import sys

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    CraftAlias,
    CraftAliasMember,
    CraftRecipeInput,
    CraftRecipeOutput,
    CraftRecipeResolved,
    CraftResolvedSnapshot,
)


def _alias_for_nesql_item(
    nesql_conn: sqlite3.Connection,
    session: Session,
    caches: dict,
    item_id: int,
    damage: int,
) -> int:
    key = (item_id, damage)
    if key in caches["alias"]:
        return caches["alias"][key]

    row = nesql_conn.execute(
        """
        SELECT o.name
        FROM nesql_oredict o
        JOIN nesql_oredict_items oi ON o.id = oi.ore_id
        WHERE oi.item_id = ?
        LIMIT 1
        """,
        (item_id,),
    ).fetchone()
    if row:
        name = str(row[0])
        aid = session.execute(select(CraftAlias.id).where(CraftAlias.key == name)).scalar_one_or_none()
        if aid is not None:
            caches["alias"][key] = int(aid)
            return int(aid)

    existing = session.execute(
        select(CraftAliasMember.alias_id).where(
            CraftAliasMember.nesql_item_id == item_id,
            CraftAliasMember.damage == damage,
        ).limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        caches["alias"][key] = int(existing)
        return int(existing)

    a = CraftAlias(key=f"_item_{item_id}_{damage}", source="nbt", priority=0)
    session.add(a)
    session.flush()
    session.add(
        CraftAliasMember(
            alias_id=a.id,
            nesql_item_id=item_id,
            damage=damage,
            weight=1,
            preferred=False,
        )
    )
    session.flush()
    caches["alias"][key] = a.id
    return int(a.id)


def _trunc_craft_recipes(session: Session) -> None:
    session.execute(delete(CraftRecipeOutput))
    session.execute(delete(CraftRecipeInput))
    session.execute(delete(CraftRecipeResolved))
    session.flush()


def _touch_snapshot(session: Session, recipes_n: int, edges_n: int) -> None:
    snap = session.get(CraftResolvedSnapshot, 1)
    now = dt.datetime.now(dt.timezone.utc)
    if snap is None:
        session.add(
            CraftResolvedSnapshot(id=1, built_at=now, recipe_count=recipes_n, edge_count=edges_n)
        )
    else:
        snap.built_at = now
        snap.recipe_count = recipes_n
        snap.edge_count = edges_n


def build(session: Session, nesql_path: str) -> tuple[int, int]:
    """Returns (recipes_inserted, edges_inserted)."""

    nesql_conn = sqlite3.connect(nesql_path)
    caches: dict = {"alias": {}}

    _trunc_craft_recipes(session)

    recipes_n = 0
    edges_n = 0

    try:
        cur = nesql_conn.execute(
            "SELECT id, recipe_type, duration, eu_per_tick, inputs_json, outputs_json "
            "FROM nesql_recipes"
        )
        for rid, rtype, duration, eu, inputs_json, outputs_json in cur:
            rid = int(rid)
            in_list = json.loads(inputs_json or "[]")
            out_list = json.loads(outputs_json or "[]")

            in_aliases: list[tuple[int, int, int, bool]] = []
            for blob in in_list:
                if not isinstance(blob, dict):
                    continue
                item_id = int(blob.get("item_id") or 0)
                if not item_id:
                    continue
                slot = int(blob.get("slot") or 0)
                dmg_row = nesql_conn.execute(
                    "SELECT damage FROM nesql_items WHERE id = ?", (item_id,)
                ).fetchone()
                dmg = int(dmg_row[0] if dmg_row and dmg_row[0] is not None else 0)
                amt = int(blob.get("amount") or 1)
                req = bool(blob.get("required", True))
                aid = _alias_for_nesql_item(nesql_conn, session, caches, item_id, dmg)
                in_aliases.append((slot, aid, amt, req))

            out_aliases: list[tuple[int, int, int, int]] = []
            for blob in out_list:
                if not isinstance(blob, dict):
                    continue
                item_id = int(blob.get("item_id") or 0)
                if not item_id:
                    continue
                slot = int(blob.get("slot") or 0)
                dmg_row = nesql_conn.execute(
                    "SELECT damage FROM nesql_items WHERE id = ?", (item_id,)
                ).fetchone()
                dmg = int(dmg_row[0] if dmg_row[0] is not None else 0) if dmg_row else 0
                amt = int(blob.get("amount") or 1)
                ch = int(blob.get("chance") or 1_000_000)
                aid = _alias_for_nesql_item(nesql_conn, session, caches, item_id, dmg)
                out_aliases.append((slot, aid, amt, ch))

            if not out_aliases:
                continue

            h = hashlib.sha256(
                json.dumps([in_aliases, out_aliases], sort_keys=True).encode()
            ).hexdigest()[:32]

            cr = CraftRecipeResolved(
                nesql_recipe_id=rid,
                machine=str(rtype) if rtype else None,
                duration_ticks=int(duration or 0),
                eu_per_tick=int(eu or 0),
                hash_inputs=h,
                preferred_cpu=None,
            )
            session.add(cr)
            session.flush()

            for slot, alias_id, amount, required in in_aliases:
                session.add(
                    CraftRecipeInput(
                        recipe_id=cr.id,
                        slot=slot,
                        alias_id=alias_id,
                        fluid_id=None,
                        amount=amount,
                        required=required,
                    )
                )
                edges_n += 1
            for slot, alias_id, amount, chance_ppm in out_aliases:
                session.add(
                    CraftRecipeOutput(
                        recipe_id=cr.id,
                        slot=slot,
                        alias_id=alias_id,
                        fluid_id=None,
                        amount=amount,
                        chance_ppm=chance_ppm,
                    )
                )
                edges_n += 1
            recipes_n += 1

        _touch_snapshot(session, recipes_n, edges_n)
        session.commit()
    finally:
        nesql_conn.close()

    return recipes_n, edges_n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nesql", required=True)
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
        r, e = build(session, args.nesql)
        print(f"build_resolved: recipes={r} io_rows={e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
