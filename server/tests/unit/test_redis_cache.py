"""Unit tests for optional NESQL Redis L1 (migration plan A6, ADR-006 §7)."""

from __future__ import annotations

import pytest

from app.core.nesql_redis_cache import (
    get_json,
    invalidate_nesql_keys,
    item_key,
    recipes_by_output_key,
    set_json,
)


@pytest.mark.asyncio
async def test_get_set_json_roundtrip():
    from fakeredis import aioredis

    r = aioredis.FakeRedis(decode_responses=True)
    k = item_key("ingotIron", 0)
    await set_json(r, k, {"id": 1, "unlocal_name": "ingotIron"})
    assert await get_json(r, k) == {"id": 1, "unlocal_name": "ingotIron"}


@pytest.mark.asyncio
async def test_get_json_none_when_redis_absent():
    assert await get_json(None, "k") is None


@pytest.mark.asyncio
async def test_set_json_noop_when_redis_absent():
    await set_json(None, "k", {})


@pytest.mark.asyncio
async def test_invalidate_nesql_prefix_deletes_only_nesql():
    from fakeredis import aioredis

    r = aioredis.FakeRedis(decode_responses=True)
    await r.set("nesql:item:x:0", "1")
    await r.set("other:k", "2")
    n = await invalidate_nesql_keys(r)
    assert n == 1
    assert await r.get("other:k") == "2"


@pytest.mark.asyncio
async def test_invalidate_returns_zero_without_redis():
    assert await invalidate_nesql_keys(None) == 0


def test_recipes_key_stable_for_same_params():
    a = recipes_by_output_key(
        output_item_id=100, input_item_id=None, recipe_type=None, limit=50, offset=0
    )
    b = recipes_by_output_key(
        output_item_id=100, input_item_id=None, recipe_type=None, limit=50, offset=0
    )
    assert a == b
    c = recipes_by_output_key(
        output_item_id=100, input_item_id=1, recipe_type=None, limit=50, offset=0
    )
    assert a != c


def test_item_key_escapes_colon_in_unlocal():
    assert item_key("a:b", 3) == "nesql:item:a_b:3"
