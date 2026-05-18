#!/usr/bin/env python3
"""One-shot copy of the main SQLite DB into PostgreSQL (ADR-006 Phase B).

Run **once** after:

1. ``alembic upgrade head`` against an empty Postgres (schema only).
2. Back up ``data/…/remote-gtnh-control.sqlite`` (or your path).

Example::

    cd server && PYTHONPATH=. python ../tools/migrate-sqlite-to-pg.py \\
        --sqlite /path/to/remote-gtnh-control.sqlite \\
        --pg-url postgresql+psycopg://gtnh:secret@localhost:5432/remote_gtnh_control

Uses SQLAlchemy ``bulk_insert_mappings`` in FK-safe table order.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Repo root: tools/migrate-sqlite-to-pg.py -> parent is remote-gtnh-control
_ROOT = Path(__file__).resolve().parent.parent
_SERVER = _ROOT / "server"
if _SERVER.is_dir():
    sys.path.insert(0, str(_SERVER))


def _sqlite_url(path: Path) -> str:
    s = path.resolve().as_posix()
    return f"sqlite:///{s}"


def _iter_models_in_fk_order():
    """ORM classes in ``Base.metadata.sorted_tables`` order."""

    from app.db.base import Base

    table_order = list(Base.metadata.sorted_tables)
    index_by_name = {t.key: i for i, t in enumerate(table_order)}
    mappers = list(Base.registry.mappers)

    def sort_key(m):
        try:
            return index_by_name[m.local_table.key]
        except KeyError:
            return 1_000_000

    for m in sorted(mappers, key=sort_key):
        yield m.class_


def _reset_sequences(session) -> None:
    """Bump Postgres serials for integer PK tables after explicit id inserts."""

    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    from app.db.base import Base

    eng = session.get_bind()
    if eng.dialect.name != "postgresql":
        return

    for mapper in Base.registry.mappers:
        table = mapper.local_table
        if table.name == "tasks":
            continue
        id_cols = [c for c in table.primary_key.columns if c.key == "id"]
        if len(id_cols) != 1:
            continue
        col = id_cols[0]
        try:
            if col.type.python_type is not int:  # type: ignore[comparison-overlap]
                continue
        except NotImplementedError:
            continue
        try:
            session.execute(
                text(
                    f'SELECT setval(pg_get_serial_sequence(\'{table.name}\', \'id\'), '
                    f'(SELECT COALESCE(MAX("id"), 1) FROM "{table.name}"))'
                )
            )
        except ProgrammingError:
            session.rollback()


def migrate(*, sqlite_path: Path, pg_url: str, dry_run: bool) -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    src_url = _sqlite_url(sqlite_path)
    src_engine = create_engine(src_url, future=True)
    dst_engine = create_engine(pg_url, future=True)

    SrcSession = sessionmaker(src_engine, future=True, expire_on_commit=False)
    DstSession = sessionmaker(dst_engine, future=True, expire_on_commit=False)

    with SrcSession() as s_src, DstSession() as s_dst:
        if dry_run:
            print("dry-run: would copy", sqlite_path, "->", pg_url)
            return
        for model in _iter_models_in_fk_order():
            table = model.__table__
            rows = s_src.execute(select(model)).scalars().all()
            if not rows:
                continue
            mappings = []
            cols = [c.key for c in model.__table__.columns]
            for row in rows:
                mappings.append({k: getattr(row, k) for k in cols})
            s_dst.bulk_insert_mappings(model, mappings)
            s_dst.commit()
            print(f"copied {len(mappings)} rows -> {table.name}")

        _reset_sequences(s_dst)
        s_dst.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite",
        type=Path,
        required=True,
        help="Path to remote-gtnh-control.sqlite",
    )
    parser.add_argument(
        "--pg-url",
        default=os.environ.get("SYNC_DATABASE_URL"),
        help="Sync SQLAlchemy URL, e.g. postgresql+psycopg://user:pw@host/db "
        "(default: env SYNC_DATABASE_URL)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intent only",
    )
    args = parser.parse_args(argv)

    if not args.sqlite.is_file():
        print("SQLite file not found:", args.sqlite, file=sys.stderr)
        return 1
    if not args.pg_url:
        print("Provide --pg-url or set SYNC_DATABASE_URL", file=sys.stderr)
        return 1

    migrate(sqlite_path=args.sqlite, pg_url=args.pg_url, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
