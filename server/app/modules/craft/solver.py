"""Resolve item goal into a minimal craft plan (ADR-006 §5, simplified)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CraftAlias,
    CraftAliasMember,
    CraftJob,
    CraftPlan,
    CraftRecipeOutput,
    CraftRecipeResolved,
)


async def build_minimal_plan(
    session: AsyncSession,
    *,
    goal_alias_id: int,
    goal_amount: int,
    client_id: str | None,
) -> tuple[CraftPlan, CraftJob, dict[str, Any]]:
    """Create an immutable ``plan_json`` plus root job row.

    If multiple recipes produce the goal alias, mark ``awaiting_choice`` with
    ``alternatives`` populated; otherwise ``ready``.
    """

    recipes = (
        await session.execute(
            select(CraftRecipeResolved)
            .join(
                CraftRecipeOutput,
                CraftRecipeOutput.recipe_id == CraftRecipeResolved.id,
            )
            .where(CraftRecipeOutput.alias_id == goal_alias_id)
        )
    ).scalars().all()

    if len(recipes) >= 2:
        alts = [{"recipe_id": r.id, "nesql_recipe_id": r.nesql_recipe_id} for r in recipes[:8]]
        plan_row = CraftPlan(
            plan_json={
                "goal_alias_id": goal_alias_id,
                "goal_amount": goal_amount,
                "stage": "awaiting_choice",
                "alternatives": alts,
            },
            status="open",
            client_id=client_id,
        )
        session.add(plan_row)
        await session.flush()
        job = CraftJob(
            parent_id=None,
            root_id=0,
            plan_id=plan_row.id,
            goal_alias_id=goal_alias_id,
            goal_amount=goal_amount,
            state="awaiting_choice",
            alternatives=alts,
            client_id=client_id,
        )
        session.add(job)
        await session.flush()
        job.root_id = job.id
        plan_row.root_job_id = job.id
        plan_row.plan_json = {
            **plan_row.plan_json,
            "root_job_id": job.id,
            "plan_id": plan_row.id,
        }
        return plan_row, job, plan_row.plan_json

    recipe_id = recipes[0].id if recipes else None
    plan_json: dict[str, Any] = {
        "goal_alias_id": goal_alias_id,
        "goal_amount": goal_amount,
        "stage": "ready",
        "chosen_recipe_id": recipe_id,
    }
    plan_row = CraftPlan(plan_json=plan_json, status="open", client_id=client_id)
    session.add(plan_row)
    await session.flush()
    job = CraftJob(
        parent_id=None,
        root_id=0,
        plan_id=plan_row.id,
        goal_alias_id=goal_alias_id,
        goal_amount=goal_amount,
        chosen_nesql_recipe_id=recipes[0].nesql_recipe_id if recipes else None,
        state="ready" if recipe_id else "failed",
        client_id=client_id,
        error=None if recipe_id else "no_recipe_for_alias",
    )
    session.add(job)
    await session.flush()
    job.root_id = job.id
    plan_row.root_job_id = job.id
    plan_json_out = {**plan_json, "root_job_id": job.id, "plan_id": plan_row.id}
    plan_row.plan_json = plan_json_out
    return plan_row, job, plan_json_out


async def get_goal_alias_id_for_item(
    session: AsyncSession, nesql_item_id: int, damage: int
) -> int | None:
    q = await session.execute(
        select(CraftAliasMember.alias_id).where(
            CraftAliasMember.nesql_item_id == nesql_item_id,
            CraftAliasMember.damage == damage,
        ).limit(1)
    )
    row = q.first()
    return int(row[0]) if row else None


async def ensure_singleton_alias(
    session: AsyncSession, nesql_item_id: int, damage: int
) -> int:
    """Return alias id for (item,damage), creating a singleton if missing."""

    existing = await get_goal_alias_id_for_item(session, nesql_item_id, damage)
    if existing is not None:
        return existing
    a = CraftAlias(key=f"_item_{nesql_item_id}_{damage}", source="nbt", priority=0)
    session.add(a)
    await session.flush()
    session.add(
        CraftAliasMember(
            alias_id=a.id,
            nesql_item_id=nesql_item_id,
            damage=damage,
            weight=1,
            preferred=False,
        )
    )
    await session.flush()
    return a.id
