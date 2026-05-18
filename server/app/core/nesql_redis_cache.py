"""Optional Redis L1 cache for hot NESQL reads (ADR-006 §7, migration plan A6)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Align with migration plan (24h).
_NESQL_TTL_SEC = 86400


def item_key(unlocal_name: str, damage: int) -> str:
    """Key for single item payload."""

    safe = (unlocal_name or "").replace(":", "_")
    return f"nesql:item:{safe}:{int(damage)}"


def recipes_by_output_key(
    *,
    output_item_id: int,
    input_item_id: int | None,
    recipe_type: str | None,
    limit: int,
    offset: int,
) -> str:
    """Stable key for :func:`search_recipes` with filters."""

    sig = json.dumps(
        [output_item_id, input_item_id, recipe_type, limit, offset],
        separators=(",", ":"),
        sort_keys=True,
    )
    h = hashlib.sha256(sig.encode()).hexdigest()[:24]
    return f"nesql:recipes_by_output:{output_item_id}:{h}"


async def get_json(redis: Any, key: str) -> Any | None:
    if redis is None:
        return None
    raw = await redis.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_json(redis: Any, key: str, value: Any) -> None:
    if redis is None:
        return
    await redis.set(
        key,
        json.dumps(value, separators=(",", ":"), default=str),
        ex=_NESQL_TTL_SEC,
    )


async def invalidate_nesql_keys(redis: Any) -> int:
    """Delete all keys matching ``nesql:*``. Returns number of keys deleted."""

    if redis is None:
        return 0
    n = 0
    async for k in redis.scan_iter(match="nesql:*"):
        await redis.delete(k)
        n += 1
    return n
