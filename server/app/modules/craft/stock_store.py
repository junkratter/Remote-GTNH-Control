"""AE inventory snapshots keyed by OC ``client_id`` (Redis optional).

Populated when ``getAllItems`` / chunked inventory tasks complete. Used by the
craft planner for AE-aware pruning and by ``GET /api/craft/me/stock``.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CraftAliasMember
from app.modules.craft.nesql_lookup import nesql_item_id_for_unlocal_name


def _redis(app: Any):
    return getattr(app.state, "redis", None) if app is not None else None


def ae_inventory_hash_key(client_id: str) -> str:
    return f"ae_inv:{client_id}"


def ae_inventory_updated_key(client_id: str) -> str:
    return f"ae_inv_updated:{client_id}"


async def replace_ae_inventory_snapshot(
    app: Any | None,
    client_id: str | None,
    flat_rows: list[dict[str, Any]],
) -> None:
    """Replace cached inventory for ``client_id`` (full snapshot per AE poll)."""

    if not client_id or app is None:
        return
    r = _redis(app)
    if r is None:
        return

    key = ae_inventory_hash_key(client_id)
    await r.delete(key)
    for row in flat_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        dmg = int(row.get("damage") or 0)
        label = str(row.get("label") or "")
        qty = int(row.get("size") or row.get("amount") or 0)
        field = f"{name}|{dmg}|{label}"
        await r.hset(key, field, str(max(qty, 0)))
    await r.set(
        ae_inventory_updated_key(client_id),
        dt.datetime.now(dt.timezone.utc).isoformat(),
    )


async def inventory_updated_iso(app: Any | None, client_id: str | None) -> str | None:
    if not client_id or app is None:
        return None
    r = _redis(app)
    if r is None:
        return None
    val = await r.get(ae_inventory_updated_key(client_id))
    if val is None:
        return None
    return val.decode("utf-8") if isinstance(val, (bytes, bytearray)) else str(val)


async def load_alias_stock_map(
    app: Any | None,
    session: AsyncSession,
    client_id: str | None,
) -> dict[int, int]:
    """Map ``craft_aliases.id`` → total quantity estimate from cached AE rows."""

    if not client_id or app is None:
        return {}
    r = _redis(app)
    if r is None:
        return {}

    raw = await r.hgetall(ae_inventory_hash_key(client_id))
    if not raw:
        return {}

    totals: dict[int, int] = {}
    for field_b, qty_b in raw.items():
        field = (
            field_b.decode("utf-8")
            if isinstance(field_b, (bytes, bytearray))
            else str(field_b)
        )
        qty_s = qty_b.decode("utf-8") if isinstance(qty_b, (bytes, bytearray)) else str(qty_b)
        try:
            qty = int(qty_s)
        except ValueError:
            qty = 0
        parts = field.split("|", 2)
        name = parts[0]
        dmg = int(parts[1]) if len(parts) > 1 else 0

        hit = await nesql_item_id_for_unlocal_name(name, dmg)
        if hit is None:
            continue
        nesql_id, odmg = hit
        aid_row = await session.execute(
            select(CraftAliasMember.alias_id).where(
                CraftAliasMember.nesql_item_id == nesql_id,
                CraftAliasMember.damage == odmg,
            ).limit(1)
        )
        aid = aid_row.scalar_one_or_none()
        if aid is None:
            continue
        totals[int(aid)] = totals.get(int(aid), 0) + max(qty, 0)

    return totals


async def alias_quantities_available(
    app: Any | None,
    session: AsyncSession,
    client_id: str | None,
    alias_ids: list[int],
) -> dict[int, int]:
    stock = await load_alias_stock_map(app, session, client_id)
    return {i: max(stock.get(i, 0), 0) for i in alias_ids}
