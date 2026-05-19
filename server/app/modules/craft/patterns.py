"""ME pattern presence checks for craft jobs (ADR-006 §9)."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AutocraftPattern, CraftAlias, CraftAliasMember, CraftRecipeOutput, CraftRecipeResolved
from app.modules.craft.nesql_lookup import unlocal_name_for_nesql_item


async def recipe_has_matching_pattern(session: AsyncSession, nesql_recipe_id: int) -> bool:
    """Return True if any stored ME pattern likely covers this resolved recipe."""

    patterns = (await session.execute(select(AutocraftPattern))).scalars().all()
    if not patterns:
        # Nothing recorded → do not block planner on missing ME rows.
        return True

    r = await session.scalar(
        select(CraftRecipeResolved).where(CraftRecipeResolved.nesql_recipe_id == nesql_recipe_id)
    )
    if r is None:
        return False

    outs = (
        await session.execute(
            select(CraftRecipeOutput).where(CraftRecipeOutput.recipe_id == r.id)
        )
    ).scalars().all()
    if not outs:
        return False

    haystack: list[str] = []
    for p in patterns:
        haystack.append(json.dumps(p.outputs or [], sort_keys=True))
        haystack.append(json.dumps(p.inputs or [], sort_keys=True))
    blob = "\n".join(haystack)

    for o in outs:
        alias = await session.get(CraftAlias, o.alias_id)
        if alias and alias.key and alias.key in blob:
            return True
        mem = await session.scalar(
            select(CraftAliasMember).where(CraftAliasMember.alias_id == o.alias_id).limit(1)
        )
        if mem is None:
            continue
        name = await unlocal_name_for_nesql_item(mem.nesql_item_id)
        if name and name in blob:
            return True

    return False
