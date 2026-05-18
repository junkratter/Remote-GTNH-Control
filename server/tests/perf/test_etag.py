"""Etag and cache headers for NESQL/quests API (see ADR-005)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client_with_nesql(tmp_path):
    """App with temporary NESQL sqlite file so ETag middleware activates."""
    import os

    import app.core.settings as settings_mod

    db = tmp_path / "t.sqlite"
    nesql = tmp_path / "nesql.sqlite"

    import sqlite3

    con = sqlite3.connect(str(nesql))
    con.execute(
        "CREATE TABLE IF NOT EXISTS nesql_import_meta "
        "(module TEXT, row_count INTEGER, imported_at TEXT)"
    )
    con.execute(
        "INSERT INTO nesql_import_meta(module, row_count, imported_at) "
        "VALUES ('items', 0, '2026-01-01')"
    )
    con.commit()
    con.close()

    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db}"
    os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["NESQL_DATABASE_URL"] = f"sqlite:///{nesql}"

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
async def test_nesql_get_has_cache_control_and_etag(client_with_nesql):
    r = await client_with_nesql.get("/api/nesql/meta")
    assert r.status_code == 200
    assert "cache-control" in {k.lower(): v for k, v in r.headers.items()}
    cc = r.headers.get("cache-control", "")
    assert "public" in cc and "max-age" in cc
    etag = r.headers.get("etag")
    assert etag and etag.startswith('W/"')

    r2 = await client_with_nesql.get(
        "/api/nesql/meta", headers={"If-None-Match": etag}
    )
    assert r2.status_code == 304
    assert r2.headers.get("etag") == etag
