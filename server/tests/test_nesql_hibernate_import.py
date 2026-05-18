"""Smoke test for Hibernate-style NESQL SCRIPT → SQLite (tools/nesql-import)."""

from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
IMPORT_SCRIPT = REPO / "tools" / "nesql-import" / "import.py"


def _load_importer():
    spec = importlib.util.spec_from_file_location("nesql_sqlite_import", IMPORT_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MINIMAL_HIBERNATE_SCRIPT = r"""
CREATE SCHEMA PUBLIC AUTHORIZATION DBA
;
INSERT INTO ITEM VALUES('i~minecraft~apple~0','img','apple',0,256,'Apple',0,64,'minecraft','','Apple','item.apple')
;
INSERT INTO FLUID VALUES('f~minecraft~water',1000,9,FALSE,'img','water','Water',0,'minecraft','',295,'fluid.water',1000)
;
INSERT INTO RECIPE_TYPE VALUES('rt~minecraft~crafting','minecraft',0,0,0,0,'',3,3,3,3,FALSE,'Workbench','i~minecraft~apple~0')
;
INSERT INTO RECIPE VALUES('r~testrecipe1','rt~minecraft~crafting')
;
INSERT INTO ITEM_GROUP VALUES('ig~root','ig~root')
;
INSERT INTO ITEM_GROUP_ITEM_STACKS VALUES('ig~root','i~minecraft~apple~0',1)
;
INSERT INTO RECIPE_ITEM_GROUP VALUES('r~testrecipe1','ig~root',0)
;
INSERT INTO RECIPE_ITEM_OUTPUTS VALUES('r~testrecipe1','i~minecraft~apple~0',1.0E0,2,0)
;
INSERT INTO QUEST_LINE VALUES('ql~line1','Line desc','Tier Start','lid1','NORMAL','i~minecraft~apple~0')
;
INSERT INTO QUEST VALUES('q~testquest1','Quest desc','Quest One','q1','AND',-1,'AND','NORMAL','i~minecraft~apple~0')
;
INSERT INTO QUEST_LINE_QUEST VALUES('ql~line1','q~testquest1')
;
INSERT INTO QUEST_LINE_QUEST_LINE_ENTRIES VALUES('ql~line1',48,72,'q~testquest1',24,24)
;
INSERT INTO QUEST_QUEST VALUES('q~testquest1','q~testquest1')
;
INSERT INTO QUEST_TASK VALUES('q~testquest1','t~task1',0)
;
INSERT INTO TASK VALUES('t~task1',FALSE,'','Gather apples',3,'CONSUME',NULL)
;
"""


@pytest.fixture
def importer():
    return _load_importer()


def test_detect_hibernate_kind(importer):
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".script",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(MINIMAL_HIBERNATE_SCRIPT)
        path = Path(f.name)
    try:
        assert importer._detect_sql_script_kind(path) == "hibernate"
    finally:
        path.unlink(missing_ok=True)


def test_hibernate_import_roundtrip(importer):
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".script",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(MINIMAL_HIBERNATE_SCRIPT)
        src = Path(f.name)
    dst = Path(tempfile.mkstemp(suffix=".sqlite")[1])
    try:
        conn = sqlite3.connect(dst)
        conn.executescript(importer.SCHEMA_DDL)
        importer._apply_nesql_migrations(conn)
        counts = importer._import_hibernate_sql(src, conn, batch=50)
        conn.close()
        assert counts["items"] >= 1
        assert counts["fluids"] >= 1
        assert counts["recipes"] >= 1
        assert counts["recipe_inputs"] >= 1
        assert counts["recipe_outputs"] >= 1
        assert counts["quests"] >= 2

        conn = sqlite3.connect(dst)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM nesql_items WHERE id = 1").fetchone()
        assert row is not None
        assert row["localized_name"] == "Apple"
        importer._materialize_recipe_json(conn)
        r = conn.execute(
            "SELECT inputs_json, outputs_json, recipe_type_label FROM nesql_recipes WHERE id = 1"
        ).fetchone()
        assert r is not None
        assert "inputs_json" in r.keys()
        assert r["recipe_type_label"] == "Workbench"
        qrows = conn.execute("SELECT COUNT(*) FROM nesql_quests").fetchone()[0]
        assert qrows >= 2
        q = conn.execute(
            "SELECT pos_x, pos_y, bq_id FROM nesql_quests WHERE id > 0 LIMIT 1"
        ).fetchone()
        assert q is not None
        assert q["pos_x"] == 48
        assert q["bq_id"] == "q1"
        assert (
            conn.execute("SELECT COUNT(*) FROM nesql_quest_edges").fetchone()[0] >= 0
        )
        conn.close()
    finally:
        src.unlink(missing_ok=True)
        dst.unlink(missing_ok=True)
