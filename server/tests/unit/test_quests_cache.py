"""Quest tree/lines in-memory cache (plan A4)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_quest_tree_second_request_does_not_query_sqlite(
    monkeypatch, client, nesql_db
):
    from app.core import quest_cache

    real = quest_cache.nesql_fetchall
    calls = {"n": 0}

    async def spy(conn, sql, params=()):
        calls["n"] += 1
        return await real(conn, sql, params)

    monkeypatch.setattr(quest_cache, "nesql_fetchall", spy)

    await client.get("/api/nesql/meta")
    await client.get("/api/quests/tree")
    n1 = calls["n"]
    assert n1 >= 2

    await client.get("/api/quests/tree")
    assert calls["n"] == n1
