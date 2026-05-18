"""HSQLDB → SQLite importer for NESQL-Exporter dumps.

Two backends:

* `--src PREFIX` (default): treat `PREFIX` as an HSQLDB file prefix
  (e.g. ``~/nesql/nesql``). Requires Java + ``jaydebeapi`` + the HSQLDB jar.

* `--source-sql FILE.sql`: read an exported SQL script (produced by
  ``SCRIPT 'file.sql'`` from HSQLDB SqlTool, or by NESQL itself).
  This mode needs **no Java**: we stream INSERT statements with a tiny parser
  and pipe them into the target SQLite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict
from typing import Iterator, Optional

DEFAULT_BATCH = 5000


def _maybe_seed_craft_aliases(nesql_sqlite: Path, enabled: bool) -> None:
    """Optional post-step: populate ``craft_aliases`` from NESQL OreDict."""

    if not enabled:
        return
    if not os.environ.get("SYNC_DATABASE_URL"):
        print(
            "[import] --seed-craft-aliases skipped: SYNC_DATABASE_URL not set",
            flush=True,
        )
        return
    import subprocess

    server_root = Path(__file__).resolve().parents[2] / "server"
    if not server_root.is_dir():
        print(f"[import] seed_aliases: server directory not found at {server_root}", flush=True)
        return
    cmd = [
        sys.executable,
        "-m",
        "app.modules.craft.seed_aliases",
        "--nesql",
        str(nesql_sqlite.resolve()),
    ]
    print("[import] running seed_aliases → SYNC_DATABASE_URL", flush=True)
    r = subprocess.run(cmd, cwd=str(server_root), env=os.environ.copy())
    if r.returncode != 0:
        print(f"[import] seed_aliases exited with code {r.returncode}", flush=True)


def _invalidate_optional_redis_nesql_cache() -> None:
    """Drop ``nesql:*`` keys after import if backend cache uses Redis (plan A6)."""

    url = os.environ.get("OPTIONAL_REDIS_URL")
    if not url:
        return
    try:
        import redis

        r = redis.Redis.from_url(url, decode_responses=True)
        deleted = 0
        for k in r.scan_iter(match="nesql:*"):
            r.delete(k)
            deleted += 1
        if deleted:
            print(f"[import] redis: deleted {deleted} nesql:* key(s)", flush=True)
    except Exception as exc:
        print(f"[import] OPTIONAL_REDIS_URL invalidate nesql:* failed: {exc}", flush=True)


SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS nesql_items (
    id INTEGER PRIMARY KEY,
    unlocal_name TEXT,
    localized_name TEXT,
    mod_id TEXT,
    damage INTEGER,
    stack_size INTEGER,
    nbt_hash TEXT
);
CREATE INDEX IF NOT EXISTS ix_nesql_items_localized ON nesql_items(localized_name);
CREATE INDEX IF NOT EXISTS ix_nesql_items_mod_id ON nesql_items(mod_id);

CREATE TABLE IF NOT EXISTS nesql_fluids (
    id INTEGER PRIMARY KEY,
    internal_name TEXT,
    localized_name TEXT,
    mod_id TEXT
);
CREATE INDEX IF NOT EXISTS ix_nesql_fluids_localized ON nesql_fluids(localized_name);

CREATE TABLE IF NOT EXISTS nesql_recipes (
    id INTEGER PRIMARY KEY,
    recipe_type TEXT,
    duration INTEGER,
    eu_per_tick INTEGER,
    inputs_json TEXT DEFAULT '[]',
    outputs_json TEXT DEFAULT '[]',
    recipe_type_label TEXT
);
CREATE INDEX IF NOT EXISTS ix_nesql_recipes_type ON nesql_recipes(recipe_type);

CREATE TABLE IF NOT EXISTS nesql_recipe_inputs (
    recipe_id INTEGER,
    slot INTEGER,
    item_id INTEGER,
    fluid_id INTEGER,
    amount INTEGER,
    PRIMARY KEY (recipe_id, slot, item_id, fluid_id)
);
CREATE INDEX IF NOT EXISTS ix_nesql_recipe_inputs_item ON nesql_recipe_inputs(item_id);
CREATE INDEX IF NOT EXISTS ix_nesql_recipe_inputs_fluid ON nesql_recipe_inputs(fluid_id);

CREATE TABLE IF NOT EXISTS nesql_recipe_outputs (
    recipe_id INTEGER,
    slot INTEGER,
    item_id INTEGER,
    fluid_id INTEGER,
    amount INTEGER,
    chance INTEGER,
    PRIMARY KEY (recipe_id, slot, item_id, fluid_id)
);
CREATE INDEX IF NOT EXISTS ix_nesql_recipe_outputs_item ON nesql_recipe_outputs(item_id);
CREATE INDEX IF NOT EXISTS ix_nesql_recipe_outputs_fluid ON nesql_recipe_outputs(fluid_id);

CREATE TABLE IF NOT EXISTS nesql_oredict (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS ix_nesql_oredict_name ON nesql_oredict(name);

CREATE TABLE IF NOT EXISTS nesql_oredict_items (
    ore_id INTEGER,
    item_id INTEGER,
    PRIMARY KEY (ore_id, item_id)
);

CREATE TABLE IF NOT EXISTS nesql_item_aspects (
    item_id INTEGER,
    aspect_name TEXT,
    amount INTEGER,
    PRIMARY KEY (item_id, aspect_name)
);
CREATE INDEX IF NOT EXISTS ix_nesql_item_aspects_aspect ON nesql_item_aspects(aspect_name);

CREATE TABLE IF NOT EXISTS nesql_quests (
    id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    quest_line INTEGER,
    parent_id INTEGER,
    task_json TEXT,
    reward_json TEXT,
    bq_id TEXT,
    pos_x INTEGER,
    pos_y INTEGER,
    size_x INTEGER,
    size_y INTEGER,
    icon_item_id INTEGER
);
CREATE INDEX IF NOT EXISTS ix_nesql_quests_parent ON nesql_quests(parent_id);
CREATE INDEX IF NOT EXISTS ix_nesql_quests_line ON nesql_quests(quest_line);
CREATE INDEX IF NOT EXISTS ix_nesql_quests_bq ON nesql_quests(bq_id);

CREATE TABLE IF NOT EXISTS nesql_quest_edges (
    from_quest_id INTEGER NOT NULL,
    to_quest_id INTEGER NOT NULL,
    PRIMARY KEY (from_quest_id, to_quest_id)
);

CREATE TABLE IF NOT EXISTS nesql_import_meta (
    module TEXT PRIMARY KEY,
    row_count INTEGER,
    imported_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _apply_nesql_migrations(sqlite_conn: sqlite3.Connection) -> None:
    """Lightweight ALTERs for DBs created before new columns existed."""
    cols = {row[1] for row in sqlite_conn.execute("PRAGMA table_info(nesql_recipes)")}
    if "recipe_type_label" not in cols:
        sqlite_conn.execute("ALTER TABLE nesql_recipes ADD COLUMN recipe_type_label TEXT")
        sqlite_conn.commit()
    qcols = {row[1] for row in sqlite_conn.execute("PRAGMA table_info(nesql_quests)")}
    for col, typ in (
        ("bq_id", "TEXT"),
        ("pos_x", "INTEGER"),
        ("pos_y", "INTEGER"),
        ("size_x", "INTEGER"),
        ("size_y", "INTEGER"),
        ("icon_item_id", "INTEGER"),
    ):
        if col not in qcols:
            sqlite_conn.execute(f"ALTER TABLE nesql_quests ADD COLUMN {col} {typ}")
    sqlite_conn.execute(
        "CREATE TABLE IF NOT EXISTS nesql_quest_edges ("
        "from_quest_id INTEGER NOT NULL, to_quest_id INTEGER NOT NULL, "
        "PRIMARY KEY (from_quest_id, to_quest_id))"
    )
    sqlite_conn.commit()


# Each module: HSQLDB-side SELECT + SQLite-side INSERT. Column order
# in SELECT must match the placeholders in INSERT.
MODULES: dict[str, dict[str, str]] = {
    "items": {
        "select": (
            "SELECT ID, UNLOCAL_NAME, LOCALIZED_NAME, MOD_ID, "
            "ITEM_DAMAGE, STACK_SIZE, NBT_HASH FROM ITEM"
        ),
        "insert": (
            "INSERT OR REPLACE INTO nesql_items "
            "(id, unlocal_name, localized_name, mod_id, damage, stack_size, nbt_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        ),
    },
    "fluids": {
        "select": "SELECT ID, INTERNAL_NAME, LOCALIZED_NAME, MOD_ID FROM FLUID",
        "insert": (
            "INSERT OR REPLACE INTO nesql_fluids "
            "(id, internal_name, localized_name, mod_id) VALUES (?, ?, ?, ?)"
        ),
    },
    "recipes": {
        "select": (
            "SELECT ID, RECIPE_TYPE, DURATION, EU_PER_TICK FROM RECIPE"
        ),
        "insert": (
            "INSERT OR REPLACE INTO nesql_recipes "
            "(id, recipe_type, duration, eu_per_tick) VALUES (?, ?, ?, ?)"
        ),
    },
    "recipe_inputs": {
        "select": (
            "SELECT RECIPE_ID, SLOT, ITEM_ID, FLUID_ID, AMOUNT FROM RECIPE_INPUT"
        ),
        "insert": (
            "INSERT OR REPLACE INTO nesql_recipe_inputs "
            "(recipe_id, slot, item_id, fluid_id, amount) VALUES (?, ?, ?, ?, ?)"
        ),
    },
    "recipe_outputs": {
        "select": (
            "SELECT RECIPE_ID, SLOT, ITEM_ID, FLUID_ID, AMOUNT, CHANCE FROM RECIPE_OUTPUT"
        ),
        "insert": (
            "INSERT OR REPLACE INTO nesql_recipe_outputs "
            "(recipe_id, slot, item_id, fluid_id, amount, chance) VALUES (?, ?, ?, ?, ?, ?)"
        ),
    },
    "oredict": {
        "select": "SELECT ID, NAME FROM ORE_DICTIONARY",
        "insert": "INSERT OR REPLACE INTO nesql_oredict (id, name) VALUES (?, ?)",
    },
    "oredict_items": {
        "select": "SELECT ORE_ID, ITEM_ID FROM ORE_DICTIONARY_ITEM",
        "insert": (
            "INSERT OR REPLACE INTO nesql_oredict_items (ore_id, item_id) VALUES (?, ?)"
        ),
    },
    "aspects": {
        "select": "SELECT ITEM_ID, ASPECT_NAME, AMOUNT FROM ITEM_ASPECT",
        "insert": (
            "INSERT OR REPLACE INTO nesql_item_aspects "
            "(item_id, aspect_name, amount) VALUES (?, ?, ?)"
        ),
    },
    "quests": {
        "select": (
            "SELECT ID, NAME, DESCRIPTION, QUEST_LINE, PARENT_ID, TASK_JSON, REWARD_JSON "
            "FROM QUEST"
        ),
        "insert": (
            "INSERT OR REPLACE INTO nesql_quests "
            "(id, name, description, quest_line, parent_id, task_json, reward_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        ),
    },
}


# Map module name -> HSQLDB table name we look for in --source-sql mode.
SQL_TABLE_FOR_MODULE = {
    "items": "ITEM",
    "fluids": "FLUID",
    "recipes": "RECIPE",
    "recipe_inputs": "RECIPE_INPUT",
    "recipe_outputs": "RECIPE_OUTPUT",
    "oredict": "ORE_DICTIONARY",
    "oredict_items": "ORE_DICTIONARY_ITEM",
    "aspects": "ITEM_ASPECT",
    "quests": "QUEST",
}


# --- HSQLDB (JDBC) backend ---------------------------------------------------


def _connect_hsqldb(src: Path, hsqldb_jar: Path):
    try:
        import jaydebeapi  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency `jaydebeapi`. Install requirements or use --source-sql."
        ) from exc

    if not hsqldb_jar.exists():
        raise SystemExit(
            f"HSQLDB jar not found at {hsqldb_jar}. Download from "
            "https://hsqldb.org/ and pass --hsqldb-jar."
        )

    url = f"jdbc:hsqldb:file:{src};readonly=true"
    return jaydebeapi.connect(
        "org.hsqldb.jdbc.JDBCDriver",
        url,
        ["SA", ""],
        str(hsqldb_jar),
    )


def _import_module_jdbc(hsql, sqlite_conn: sqlite3.Connection, name: str, batch: int) -> int:
    cfg = MODULES[name]
    print(f"[{name}] starting (jdbc)", flush=True)
    cursor = hsql.cursor()
    cursor.execute(cfg["select"])
    rows = 0
    while True:
        chunk = cursor.fetchmany(batch)
        if not chunk:
            break
        sqlite_conn.executemany(cfg["insert"], chunk)
        sqlite_conn.commit()
        rows += len(chunk)
        print(f"[{name}] +{len(chunk)} (total {rows})", flush=True)
    cursor.close()
    return rows


# --- SQL-script backend ------------------------------------------------------


_INSERT_RE = re.compile(
    r"^INSERT INTO\s+(?P<table>[A-Z_]+)\s+VALUES\s*\((?P<vals>.+)\)\s*;?\s*$",
    re.IGNORECASE,
)


def _split_values(raw: str) -> list:
    """Split a single VALUES(...) tuple into Python values.

    Handles HSQLDB quirks: strings in single quotes with '' escaping,
    NULL, integers, and HEX'..' literals (treated as raw bytes -> hex str).
    """
    out: list = []
    buf = []
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == " " or ch == "\t":
            i += 1
            continue
        if ch == ",":
            i += 1
            continue
        if ch == "'":
            j = i + 1
            chars = []
            while j < n:
                if raw[j] == "'":
                    if j + 1 < n and raw[j + 1] == "'":
                        chars.append("'")
                        j += 2
                        continue
                    break
                chars.append(raw[j])
                j += 1
            out.append("".join(chars))
            i = j + 1
        elif raw[i:i + 5].upper() == "NULL,":
            out.append(None)
            i += 5
        elif raw[i:i + 4].upper() == "NULL":
            out.append(None)
            i += 4
        else:
            # numeric / hex / boolean — read until comma or end
            j = i
            while j < n and raw[j] not in ",":
                j += 1
            token = raw[i:j].strip()
            if not token:
                i = j
                continue
            up = token.upper()
            if up == "TRUE":
                out.append(1)
            elif up == "FALSE":
                out.append(0)
            elif up.startswith("X'") or up.startswith("HEX'"):
                # bytes literal - skip blobs in the SQL-script path
                out.append(None)
            else:
                try:
                    out.append(int(token))
                except ValueError:
                    try:
                        out.append(float(token))
                    except ValueError:
                        out.append(token)
            i = j
    return out


def _iter_insert_rows(script: Path, table: str) -> Iterator[list]:
    table_up = table.upper()
    with script.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("INSERT INTO ") and not line.startswith("insert into "):
                continue
            m = _INSERT_RE.match(line.strip())
            if not m or m.group("table").upper() != table_up:
                continue
            yield _split_values(m.group("vals"))


def _import_module_sql(
    script: Path,
    sqlite_conn: sqlite3.Connection,
    name: str,
    batch: int,
) -> int:
    table = SQL_TABLE_FOR_MODULE[name]
    cfg = MODULES[name]
    expected_cols = cfg["insert"].count("?")
    print(f"[{name}] starting (sql-script, table={table}, cols={expected_cols})", flush=True)
    rows = 0
    chunk: list = []
    for vals in _iter_insert_rows(script, table):
        if len(vals) < expected_cols:
            vals = vals + [None] * (expected_cols - len(vals))
        elif len(vals) > expected_cols:
            vals = vals[:expected_cols]
        chunk.append(tuple(vals))
        if len(chunk) >= batch:
            sqlite_conn.executemany(cfg["insert"], chunk)
            sqlite_conn.commit()
            rows += len(chunk)
            print(f"[{name}] +{len(chunk)} (total {rows})", flush=True)
            chunk.clear()
    if chunk:
        sqlite_conn.executemany(cfg["insert"], chunk)
        sqlite_conn.commit()
        rows += len(chunk)
        print(f"[{name}] +{len(chunk)} (total {rows})", flush=True)
    return rows


# --- GTNH nesql-exporter (Hibernate) SQL script ----------------------------


def _detect_sql_script_kind(script: Path) -> str:
    """Return ``legacy`` (integer IDs, flat RECIPE_INPUT) or ``hibernate`` (string IDs)."""
    for vals in _iter_insert_rows(script, "ITEM"):
        if len(vals) >= 12 and isinstance(vals[0], str):
            return "hibernate"
        break
    return "legacy"


def _nbt_short_hash(nbt_val: object) -> Optional[str]:
    if nbt_val is None or nbt_val == "":
        return None
    return hashlib.sha256(str(nbt_val).encode("utf-8", errors="replace")).hexdigest()[:24]


def _prob_to_chance_percent(prob: object) -> int:
    try:
        p = float(prob)
    except (TypeError, ValueError):
        return 100
    return max(0, min(100, int(round(p * 100))))


def _hibernate_scan(script: Path) -> tuple[set, set, set, dict, dict]:
    """Collect entity string IDs and group expansion tables (one full-file pass)."""
    item_sids: set = set()
    fluid_sids: set = set()
    recipe_sids: set = set()
    item_group_stacks: dict[str, list[tuple[str, int]]] = defaultdict(list)
    fluid_group_stacks: dict[str, list[tuple[str, int]]] = defaultdict(list)
    item_ref_extra: set = set()
    fluid_ref_extra: set = set()

    with script.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("INSERT INTO ") and not line.startswith("insert into "):
                continue
            m = _INSERT_RE.match(line.strip())
            if not m:
                continue
            t = m.group("table").upper()
            vals = _split_values(m.group("vals"))
            if t == "ITEM" and len(vals) >= 12:
                item_sids.add(vals[0])
            elif t == "FLUID" and len(vals) >= 13:
                fluid_sids.add(vals[0])
            elif t == "RECIPE" and len(vals) >= 2:
                recipe_sids.add(vals[0])
            elif t == "ITEM_GROUP_ITEM_STACKS" and len(vals) >= 3:
                ig, it, sz = vals[0], vals[1], vals[2]
                item_group_stacks[str(ig)].append(
                    (str(it), int(sz) if sz is not None else 1)
                )
                item_ref_extra.add(str(it))
            elif t == "FLUID_GROUP_FLUID_STACKS" and len(vals) >= 3:
                fg, amt, fl = vals[0], vals[1], vals[2]
                fluid_group_stacks[str(fg)].append(
                    (str(fl), int(amt) if amt is not None else 1)
                )
                fluid_ref_extra.add(str(fl))
            elif t == "RECIPE_ITEM_INPUTS_ITEMS" and len(vals) >= 2:
                item_ref_extra.add(str(vals[1]))
            elif t == "RECIPE_ITEM_OUTPUTS" and len(vals) >= 2:
                item_ref_extra.add(str(vals[1]))
            elif t == "RECIPE_FLUID_INPUTS_FLUIDS" and len(vals) >= 2:
                fluid_ref_extra.add(str(vals[1]))
            elif t == "RECIPE_FLUID_OUTPUTS" and len(vals) >= 3:
                fluid_ref_extra.add(str(vals[2]))

    item_sids |= {s for s in item_ref_extra if isinstance(s, str) and s.startswith("i~")}
    fluid_sids |= {s for s in fluid_ref_extra if isinstance(s, str) and s.startswith("f~")}
    return item_sids, fluid_sids, recipe_sids, item_group_stacks, fluid_group_stacks


def _assign_stable_int_ids(sids: set) -> dict[str, int]:
    return {sid: i + 1 for i, sid in enumerate(sorted(sids))}


RECIPE_INSERT_HIBERNATE = (
    "INSERT OR REPLACE INTO nesql_recipes "
    "(id, recipe_type, duration, eu_per_tick, recipe_type_label, inputs_json, outputs_json) "
    "VALUES (?, ?, ?, ?, ?, '[]', '[]')"
)


def _hibernate_load_recipe_type_labels(script: Path) -> dict[str, str]:
    """Map RECIPE_TYPE id (rt~...) → human-readable TYPE column."""
    out: dict[str, str] = {}
    with script.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not (
                line.startswith("INSERT INTO ")
                or line.startswith("insert into ")
            ):
                continue
            m = _INSERT_RE.match(line.strip())
            if not m or m.group("table").upper() != "RECIPE_TYPE":
                continue
            vals = _split_values(m.group("vals"))
            if len(vals) < 13:
                continue
            rid = str(vals[0])
            label = vals[12]
            if isinstance(label, str) and label.strip():
                out[rid] = label.strip()
    return out


def _hibernate_import_quests(
    script: Path,
    sqlite_conn: sqlite3.Connection,
    batch: int,
    item_map: dict[str, int],
    ig_stacks: dict[str, list[tuple[str, int]]],
) -> int:
    """Import QUEST / QUEST_LINE / tasks into ``nesql_quests`` (GTNH Hibernate export)."""
    sqlite_conn.execute("DELETE FROM nesql_quest_edges")
    sqlite_conn.commit()
    ORPHAN = "__orphan_quest_line__"
    line_order: list[str] = []
    line_seen: set[str] = set()
    line_meta: dict[str, tuple[str, str]] = {}
    line_bq_id: dict[str, str] = {}
    quest_meta: dict[str, tuple[str, str, str, str | None]] = {}
    quest_to_line: dict[str, str] = {}
    quest_positions: dict[str, tuple[int, int, int, int]] = {}
    quest_edges_raw: list[tuple[str, str]] = []
    quest_tasks_raw: dict[str, list[tuple[int, str]]] = defaultdict(list)
    task_meta: dict[str, dict] = {}
    task_item_groups: dict[str, list[str]] = defaultdict(list)
    quest_rewards_raw: dict[str, list[tuple[int, str]]] = defaultdict(list)
    reward_meta: dict[str, dict] = {}
    reward_item_groups: dict[str, list[str]] = defaultdict(list)

    def _resolve_ig_items(ig_sid: str) -> list[dict]:
        out: list[dict] = []
        seen: set[tuple[int, int]] = set()
        for isid, amt in ig_stacks.get(str(ig_sid), []):
            iid = item_map.get(isid)
            if iid is None:
                continue
            key = (iid, int(amt) if amt is not None else 1)
            if key in seen:
                continue
            seen.add(key)
            out.append({"item_id": iid, "amount": key[1]})
        return out

    with script.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not (
                line.startswith("INSERT INTO ")
                or line.startswith("insert into ")
            ):
                continue
            m = _INSERT_RE.match(line.strip())
            if not m:
                continue
            t = m.group("table").upper()
            vals = _split_values(m.group("vals"))
            if t == "QUEST_LINE" and len(vals) >= 6:
                sid = str(vals[0])
                desc, name = str(vals[1]), str(vals[2])
                if sid not in line_seen:
                    line_seen.add(sid)
                    line_order.append(sid)
                line_meta[sid] = (name, desc)
                line_bq_id[sid] = str(vals[3])
            elif t == "QUEST" and len(vals) >= 9:
                qs = str(vals[0])
                icon = vals[8]
                quest_meta[qs] = (
                    str(vals[2]),
                    str(vals[1]),
                    str(vals[3]),
                    str(icon) if icon is not None and str(icon) else None,
                )
            elif t == "QUEST_QUEST" and len(vals) >= 2:
                quest_edges_raw.append((str(vals[1]), str(vals[0])))
            elif t == "QUEST_LINE_QUEST" and len(vals) >= 2:
                ql, q = str(vals[0]), str(vals[1])
                if q not in quest_to_line:
                    quest_to_line[q] = ql
            elif t == "QUEST_LINE_QUEST_LINE_ENTRIES" and len(vals) >= 6:
                ql = str(vals[0])
                qq = vals[3]
                if qq is not None and str(qq):
                    qqs = str(qq)
                    if qqs not in quest_to_line:
                        quest_to_line[qqs] = ql
                    try:
                        quest_positions[qqs] = (
                            int(vals[1]),
                            int(vals[2]),
                            int(vals[4]),
                            int(vals[5]),
                        )
                    except (TypeError, ValueError):
                        pass
            elif t == "QUEST_TASK" and len(vals) >= 3:
                try:
                    order = int(vals[2])
                except (TypeError, ValueError):
                    order = 0
                quest_tasks_raw[str(vals[0])].append((order, str(vals[1])))
            elif t == "TASK" and len(vals) >= 6:
                tid = str(vals[0])
                task_meta[tid] = {
                    "name": str(vals[3]),
                    "type": str(vals[5]),
                    "number_required": vals[4],
                    "dimension": str(vals[2]),
                }
            elif t == "TASK_ITEM_GROUP" and len(vals) >= 2:
                task_item_groups[str(vals[0])].append(str(vals[1]))
            elif t == "QUEST_REWARD" and len(vals) >= 3:
                try:
                    ro = int(vals[2])
                except (TypeError, ValueError):
                    ro = 0
                quest_rewards_raw[str(vals[0])].append((ro, str(vals[1])))
            elif t == "REWARD" and len(vals) >= 7:
                rid = str(vals[0])
                reward_meta[rid] = {
                    "name": str(vals[4]),
                    "type": str(vals[5]),
                    "xp": vals[6],
                    "command": str(vals[1]),
                }
            elif t == "REWARD_ITEM_GROUP" and len(vals) >= 2:
                reward_item_groups[str(vals[0])].append(str(vals[1]))

    for ql in set(quest_to_line.values()):
        if ql not in line_meta:
            line_meta[ql] = (ql[:80], "")

    for qs in quest_meta:
        if qs not in quest_to_line:
            quest_to_line[qs] = ORPHAN
    if ORPHAN in set(quest_to_line.values()):
        if ORPHAN not in line_meta:
            line_meta[ORPHAN] = ("Other", "")
        if ORPHAN not in line_seen:
            line_order.append(ORPHAN)

    lines_ordered: list[str] = list(line_order)
    for sid in sorted(line_meta.keys()):
        if sid not in line_seen:
            lines_ordered.append(sid)

    line_ids = {sid: i + 1 for i, sid in enumerate(lines_ordered)}
    quest_ids = {sid: i + 1 for i, sid in enumerate(sorted(quest_meta.keys()))}

    q_ins = (
        "INSERT OR REPLACE INTO nesql_quests "
        "(id, name, description, quest_line, parent_id, task_json, reward_json, "
        "bq_id, pos_x, pos_y, size_x, size_y, icon_item_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    chunk: list = []

    def flush() -> None:
        nonlocal chunk
        if not chunk:
            return
        sqlite_conn.executemany(q_ins, chunk)
        sqlite_conn.commit()
        chunk.clear()

    for sid in lines_ordered:
        lid = line_ids[sid]
        name, desc = line_meta.get(sid, (sid, ""))
        root_id = -lid
        chunk.append(
            (
                root_id,
                name,
                desc,
                lid,
                None,
                "[]",
                "[]",
                line_bq_id.get(sid),
                None,
                None,
                None,
                None,
                None,
            )
        )
        if len(chunk) >= batch:
            flush()

    for qs in sorted(quest_meta.keys()):
        qid = quest_ids[qs]
        nm, desc, bq_id, icon_sid = quest_meta[qs]
        lsid = quest_to_line[qs]
        lid = line_ids.get(lsid, 1)
        parent_id = -lid
        pos = quest_positions.get(qs)
        icon_iid = item_map.get(icon_sid) if icon_sid else None
        tasks = []
        for _ord, tid in sorted(quest_tasks_raw.get(qs, [])):
            meta = task_meta.get(tid)
            if not meta:
                continue
            row = dict(meta)
            items: list[dict] = []
            for ig in task_item_groups.get(tid, []):
                items.extend(_resolve_ig_items(ig))
            if items:
                row["items"] = items
            tasks.append(row)
        rewards = []
        for _ord, rid in sorted(quest_rewards_raw.get(qs, [])):
            meta = reward_meta.get(rid)
            if not meta:
                continue
            row = dict(meta)
            items: list[dict] = []
            for ig in reward_item_groups.get(rid, []):
                items.extend(_resolve_ig_items(ig))
            if items:
                row["items"] = items
            rewards.append(row)
        chunk.append(
            (
                qid,
                nm,
                desc,
                lid,
                parent_id,
                json.dumps(tasks, separators=(",", ":")),
                json.dumps(rewards, separators=(",", ":")),
                bq_id,
                pos[0] if pos else None,
                pos[1] if pos else None,
                pos[2] if pos else 24,
                pos[3] if pos else 24,
                icon_iid,
            )
        )
        if len(chunk) >= batch:
            flush()
    flush()

    edge_chunk: list[tuple[int, int]] = []
    for req_sid, by_sid in quest_edges_raw:
        f_id = quest_ids.get(req_sid)
        t_id = quest_ids.get(by_sid)
        if f_id is None or t_id is None:
            continue
        edge_chunk.append((f_id, t_id))
        if len(edge_chunk) >= batch:
            sqlite_conn.executemany(
                "INSERT OR IGNORE INTO nesql_quest_edges (from_quest_id, to_quest_id) "
                "VALUES (?, ?)",
                edge_chunk,
            )
            sqlite_conn.commit()
            edge_chunk.clear()
    if edge_chunk:
        sqlite_conn.executemany(
            "INSERT OR IGNORE INTO nesql_quest_edges (from_quest_id, to_quest_id) "
            "VALUES (?, ?)",
            edge_chunk,
        )
        sqlite_conn.commit()

    total = len(line_ids) + len(quest_ids)
    print(
        f"[hibernate] quests: {len(line_ids)} lines + {len(quest_ids)} quests, "
        f"{len(quest_edges_raw)} edge rows",
        flush=True,
    )
    return total


def _import_hibernate_sql(
    script: Path,
    sqlite_conn: sqlite3.Connection,
    batch: int,
) -> dict[str, int]:
    """Import GTNH Hibernate-style HSQLDB SCRIPT into our SQLite schema."""
    print("[hibernate] scanning script…", flush=True)
    item_sids, fluid_sids, recipe_sids, ig_stacks, fg_stacks = _hibernate_scan(script)
    item_map = _assign_stable_int_ids(item_sids)
    fluid_map = _assign_stable_int_ids(fluid_sids)
    recipe_map = _assign_stable_int_ids(recipe_sids)
    print(
        f"[hibernate] ids: items={len(item_map)} fluids={len(fluid_map)} "
        f"recipes={len(recipe_map)}",
        flush=True,
    )

    counts: dict[str, int] = defaultdict(int)
    item_ins = MODULES["items"]["insert"]
    fluid_ins = MODULES["fluids"]["insert"]
    ri_ins = MODULES["recipe_inputs"]["insert"]
    ro_ins = MODULES["recipe_outputs"]["insert"]

    type_labels = _hibernate_load_recipe_type_labels(script)
    print(f"[hibernate] recipe types: {len(type_labels)}", flush=True)

    def flush_many(sql: str, chunk: list) -> None:
        if not chunk:
            return
        sqlite_conn.executemany(sql, chunk)
        sqlite_conn.commit()

    # --- Pass 2: core tables ---
    chunk_i: list = []
    chunk_f: list = []
    chunk_r: list = []
    with script.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not (
                line.startswith("INSERT INTO ")
                or line.startswith("insert into ")
            ):
                continue
            m = _INSERT_RE.match(line.strip())
            if not m:
                continue
            t = m.group("table").upper()
            vals = _split_values(m.group("vals"))
            if t == "ITEM" and len(vals) >= 12:
                sid = vals[0]
                nid = item_map.get(sid)
                if nid is None:
                    continue
                chunk_i.append(
                    (
                        nid,
                        vals[11],
                        vals[5],
                        vals[8],
                        vals[3],
                        vals[7],
                        _nbt_short_hash(vals[9]),
                    )
                )
                if len(chunk_i) >= batch:
                    flush_many(item_ins, chunk_i)
                    counts["items"] += len(chunk_i)
                    print(f"[hibernate] items +{len(chunk_i)} (total {counts['items']})", flush=True)
                    chunk_i.clear()
            elif t == "FLUID" and len(vals) >= 13:
                sid = vals[0]
                nid = fluid_map.get(sid)
                if nid is None:
                    continue
                chunk_f.append((nid, vals[5], vals[6], vals[8]))
                if len(chunk_f) >= batch:
                    flush_many(fluid_ins, chunk_f)
                    counts["fluids"] += len(chunk_f)
                    print(f"[hibernate] fluids +{len(chunk_f)} (total {counts['fluids']})", flush=True)
                    chunk_f.clear()
            elif t == "RECIPE" and len(vals) >= 2:
                sid = vals[0]
                nid = recipe_map.get(sid)
                if nid is None:
                    continue
                rtid = str(vals[1])
                label = type_labels.get(rtid, "")
                chunk_r.append((nid, rtid, 0, 0, label))
                if len(chunk_r) >= batch:
                    flush_many(RECIPE_INSERT_HIBERNATE, chunk_r)
                    counts["recipes"] += len(chunk_r)
                    print(f"[hibernate] recipes +{len(chunk_r)} (total {counts['recipes']})", flush=True)
                    chunk_r.clear()
    flush_many(item_ins, chunk_i)
    counts["items"] += len(chunk_i)
    flush_many(fluid_ins, chunk_f)
    counts["fluids"] += len(chunk_f)
    flush_many(RECIPE_INSERT_HIBERNATE, chunk_r)
    counts["recipes"] += len(chunk_r)
    print(
        f"[hibernate] core done: items={counts['items']} fluids={counts['fluids']} "
        f"recipes={counts['recipes']}",
        flush=True,
    )

    # --- Pass 3: recipe inputs / outputs ---
    recipes_using_groups: set[int] = set()
    with script.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("INSERT INTO RECIPE_ITEM_GROUP"):
                continue
            m = _INSERT_RE.match(line.strip())
            if not m:
                continue
            vals = _split_values(m.group("vals"))
            if len(vals) < 2:
                continue
            rid = recipe_map.get(str(vals[0]))
            if rid is not None:
                recipes_using_groups.add(rid)

    slot_next: dict[int, int] = defaultdict(int)
    used_grid_slots: dict[int, set[int]] = defaultdict(set)

    def next_slot(rid: int) -> int:
        s = slot_next[rid]
        slot_next[rid] = s + 1
        return s

    chunk_in: list = []
    chunk_out: list = []

    def add_input(
        rid: int,
        item_id: Optional[int],
        fluid_id: Optional[int],
        amount: int,
        grid_slot: Optional[int] = None,
    ) -> None:
        if grid_slot is not None:
            slot = int(grid_slot)
            if slot in used_grid_slots[rid]:
                return
            used_grid_slots[rid].add(slot)
        else:
            slot = next_slot(rid)
        chunk_in.append((rid, slot, item_id, fluid_id, amount))
        if len(chunk_in) >= batch:
            flush_many(ri_ins, chunk_in)
            counts["recipe_inputs"] += len(chunk_in)
            print(
                f"[hibernate] recipe_inputs +{len(chunk_in)} "
                f"(total {counts['recipe_inputs']})",
                flush=True,
            )
            chunk_in.clear()

    def add_output(
        rid: int,
        item_id: Optional[int],
        fluid_id: Optional[int],
        amount: int,
        chance: int,
    ) -> None:
        chunk_out.append((rid, next_slot(rid), item_id, fluid_id, amount, chance))
        if len(chunk_out) >= batch:
            flush_many(ro_ins, chunk_out)
            counts["recipe_outputs"] += len(chunk_out)
            print(
                f"[hibernate] recipe_outputs +{len(chunk_out)} "
                f"(total {counts['recipe_outputs']})",
                flush=True,
            )
            chunk_out.clear()

    with script.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not (
                line.startswith("INSERT INTO ")
                or line.startswith("insert into ")
            ):
                continue
            m = _INSERT_RE.match(line.strip())
            if not m:
                continue
            t = m.group("table").upper()
            vals = _split_values(m.group("vals"))
            if t == "RECIPE_ITEM_INPUTS_ITEMS" and len(vals) >= 2:
                rs, isid = vals[0], vals[1]
                rid = recipe_map.get(rs)
                if rid is None or rid in recipes_using_groups:
                    continue
                iid = item_map.get(isid)
                if iid is None:
                    continue
                add_input(rid, iid, None, 1)
            elif t == "RECIPE_FLUID_INPUTS_FLUIDS" and len(vals) >= 2:
                rs, fsid = vals[0], vals[1]
                rid = recipe_map.get(rs)
                fid = fluid_map.get(fsid)
                if rid is None or fid is None:
                    continue
                add_input(rid, None, fid, 1000)
            elif t == "RECIPE_ITEM_GROUP" and len(vals) >= 3:
                rs, ig = vals[0], vals[1]
                grid_key = vals[2]
                rid = recipe_map.get(rs)
                if rid is None:
                    continue
                try:
                    grid_slot = int(grid_key)
                except (TypeError, ValueError):
                    grid_slot = None
                stacks = ig_stacks.get(str(ig), [])
                if not stacks:
                    continue
                isid, amt = stacks[0]
                iid = item_map.get(isid)
                if iid is None:
                    continue
                add_input(rid, iid, None, int(amt) if amt else 1, grid_slot)
            elif t == "RECIPE_FLUID_GROUP" and len(vals) >= 2:
                rs, fg = vals[0], vals[1]
                rid = recipe_map.get(rs)
                if rid is None:
                    continue
                for fsid, amt in fg_stacks.get(str(fg), []):
                    fid = fluid_map.get(fsid)
                    if fid is None:
                        continue
                    add_input(rid, None, fid, amt)
            elif t == "RECIPE_ITEM_OUTPUTS" and len(vals) >= 5:
                rs, isid = vals[0], vals[1]
                prob, stack, _key = vals[2], vals[3], vals[4]
                rid = recipe_map.get(rs)
                iid = item_map.get(isid)
                if rid is None or iid is None:
                    continue
                try:
                    amt = int(stack)
                except (TypeError, ValueError):
                    amt = 1
                add_output(rid, iid, None, amt, _prob_to_chance_percent(prob))
            elif t == "RECIPE_FLUID_OUTPUTS" and len(vals) >= 5:
                rs, amt, fsid, prob, _key = vals[0], vals[1], vals[2], vals[3], vals[4]
                rid = recipe_map.get(rs)
                fid = fluid_map.get(fsid)
                if rid is None or fid is None:
                    continue
                try:
                    amount = int(amt)
                except (TypeError, ValueError):
                    amount = 1
                add_output(rid, None, fid, amount, _prob_to_chance_percent(prob))

    flush_many(ri_ins, chunk_in)
    counts["recipe_inputs"] += len(chunk_in)
    flush_many(ro_ins, chunk_out)
    counts["recipe_outputs"] += len(chunk_out)
    print(
        f"[hibernate] io done: inputs={counts['recipe_inputs']} "
        f"outputs={counts['recipe_outputs']}",
        flush=True,
    )

    counts["oredict"] = 0
    counts["oredict_items"] = 0
    counts["aspects"] = 0
    counts["quests"] = _hibernate_import_quests(
        script, sqlite_conn, batch, item_map, ig_stacks
    )
    return dict(counts)


# --- Post-processing ---------------------------------------------------------


def _materialize_recipe_json(sqlite_conn: sqlite3.Connection) -> None:
    """Fold ``recipe_inputs`` / ``recipe_outputs`` into ``nesql_recipes.*_json``.

    Lets the API return a single row per recipe without an extra join.
    """
    print("[post] building recipe inputs/outputs JSON", flush=True)

    def _agg(table: str, with_chance: bool) -> dict[int, list[dict]]:
        cols = "recipe_id, slot, item_id, fluid_id, amount"
        if with_chance:
            cols += ", chance"
        cursor = sqlite_conn.execute(
            f"SELECT {cols} FROM {table} ORDER BY recipe_id, slot"
        )
        out: dict[int, list[dict]] = {}
        for row in cursor:
            recipe_id = row[0]
            entry = {
                "slot": row[1],
                "item_id": row[2],
                "fluid_id": row[3],
                "amount": row[4],
            }
            if with_chance:
                entry["chance"] = row[5]
            out.setdefault(recipe_id, []).append(entry)
        return out

    inputs = _agg("nesql_recipe_inputs", with_chance=False)
    outputs = _agg("nesql_recipe_outputs", with_chance=True)
    affected = sorted(set(inputs) | set(outputs))
    rows = 0
    for recipe_id in affected:
        sqlite_conn.execute(
            "UPDATE nesql_recipes SET inputs_json = ?, outputs_json = ? WHERE id = ?",
            (
                json.dumps(inputs.get(recipe_id, []), separators=(",", ":")),
                json.dumps(outputs.get(recipe_id, []), separators=(",", ":")),
                recipe_id,
            ),
        )
        rows += 1
        if rows % 5000 == 0:
            sqlite_conn.commit()
            print(f"[post] materialized {rows}", flush=True)
    sqlite_conn.commit()
    print(f"[post] materialized {rows} recipes total", flush=True)


def _record_meta(sqlite_conn: sqlite3.Connection, module: str, count: int) -> None:
    sqlite_conn.execute(
        "INSERT OR REPLACE INTO nesql_import_meta (module, row_count, imported_at) "
        "VALUES (?, ?, CURRENT_TIMESTAMP)",
        (module, count),
    )
    sqlite_conn.commit()


def _build_fts_indexes(sqlite_conn: sqlite3.Connection) -> None:
    """FTS5 mirrors for item and quest search (plan A3)."""
    sqlite_conn.executescript(
        """
        DROP TABLE IF EXISTS nesql_items_fts;
        CREATE VIRTUAL TABLE nesql_items_fts USING fts5(
            localized_name, unlocal_name,
            content='nesql_items', content_rowid='id', tokenize='unicode61'
        );
        INSERT INTO nesql_items_fts(rowid, localized_name, unlocal_name)
            SELECT id, localized_name, unlocal_name FROM nesql_items;

        DROP TABLE IF EXISTS nesql_quests_fts;
        CREATE VIRTUAL TABLE nesql_quests_fts USING fts5(
            name, description,
            content='nesql_quests', content_rowid='id', tokenize='unicode61'
        );
        INSERT INTO nesql_quests_fts(rowid, name, description)
            SELECT id, name, description FROM nesql_quests;
        """
    )
    sqlite_conn.execute(
        "INSERT OR REPLACE INTO nesql_import_meta (module, row_count, imported_at) "
        "VALUES ('_fts', 1, CURRENT_TIMESTAMP)"
    )
    sqlite_conn.commit()


# --- CLI ---------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--src", type=Path, help="HSQLDB file prefix (no extension)")
    src.add_argument(
        "--source-sql",
        type=Path,
        help="Path to an SQL script produced by HSQLDB's SCRIPT command (no Java needed)",
    )

    parser.add_argument("--dst", type=Path, required=True, help="Target SQLite path")
    parser.add_argument(
        "--hsqldb-jar",
        type=Path,
        default=Path(__file__).parent / "vendor" / "hsqldb.jar",
    )
    parser.add_argument(
        "--modules",
        type=str,
        default=",".join(MODULES.keys()),
        help="Comma-separated list of modules to import.",
    )
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    parser.add_argument(
        "--no-materialize",
        action="store_true",
        help="Skip building inputs_json / outputs_json on nesql_recipes",
    )
    parser.add_argument(
        "--seed-craft-aliases",
        action="store_true",
        help="After import, run server craft alias seed (needs SYNC_DATABASE_URL; see seed_aliases).",
    )
    args = parser.parse_args()

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    sqlite_conn = sqlite3.connect(args.dst)
    sqlite_conn.executescript(SCHEMA_DDL)
    _apply_nesql_migrations(sqlite_conn)

    requested = [m.strip() for m in args.modules.split(",") if m.strip()]
    unknown = set(requested) - set(MODULES.keys())
    if unknown:
        raise SystemExit(f"Unknown modules: {sorted(unknown)}")

    hibernate_import = False
    try:
        if args.source_sql:
            if not args.source_sql.exists():
                raise SystemExit(f"SQL script not found: {args.source_sql}")
            kind = _detect_sql_script_kind(args.source_sql)
            if kind == "hibernate":
                hibernate_import = True
                print(
                    "[import] detected Hibernate / GTNH nesql-exporter script "
                    "(string IDs; --modules ignored for this format)",
                    flush=True,
                )
                counts = _import_hibernate_sql(args.source_sql, sqlite_conn, args.batch)
                for mod, c in sorted(counts.items()):
                    _record_meta(sqlite_conn, mod, c)
            else:
                for name in requested:
                    count = _import_module_sql(args.source_sql, sqlite_conn, name, args.batch)
                    _record_meta(sqlite_conn, name, count)
        else:
            hsql = _connect_hsqldb(args.src, args.hsqldb_jar)
            try:
                for name in requested:
                    count = _import_module_jdbc(hsql, sqlite_conn, name, args.batch)
                    _record_meta(sqlite_conn, name, count)
            finally:
                hsql.close()

        if not args.no_materialize and (
            hibernate_import
            or {"recipes", "recipe_inputs", "recipe_outputs"} <= set(requested)
        ):
            _materialize_recipe_json(sqlite_conn)
        _build_fts_indexes(sqlite_conn)
        _invalidate_optional_redis_nesql_cache()
        _maybe_seed_craft_aliases(args.dst, args.seed_craft_aliases)
    finally:
        sqlite_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
