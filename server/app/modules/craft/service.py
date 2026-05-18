"""Craft service — plans, lifecycle."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import READY
from app.core.tasks import task_store
from app.db.models import CraftAliasMember, CraftJob, CraftPlan
from app.modules.autocraft.service import build_request_command
from app.modules.craft import solver
from app.modules.craft.nesql_lookup import unlocal_name_for_nesql_item
from app.modules.craft.state_machine import assert_transition_ok


async def create_plan(
    session: AsyncSession,
    *,
    goal_alias_id: int,
    amount: int,
    client_id: str | None,
) -> tuple[CraftPlan, CraftJob, dict[str, Any]]:
    plan, job, pj = await solver.build_minimal_plan(
        session,
        goal_alias_id=goal_alias_id,
        goal_amount=amount,
        client_id=client_id,
    )
    await session.commit()
    await session.refresh(plan)
    await session.refresh(job)
    return plan, job, pj


async def get_plan_tree(session: AsyncSession, root_job_id: int) -> dict[str, Any] | None:
    job = await session.get(CraftJob, root_job_id)
    if job is None:
        return None
    plan = await session.get(CraftPlan, job.plan_id)
    if plan is None:
        return None
    children = (
        await session.execute(select(CraftJob).where(CraftJob.root_id == job.root_id))
    ).scalars().all()
    return {
        "plan": plan.plan_json,
        "jobs": [
            {
                "id": j.id,
                "state": j.state,
                "goal_alias_id": j.goal_alias_id,
                "task_id": j.task_id,
                "alternatives": j.alternatives,
            }
            for j in children
        ],
    }


async def choose_alternative(
    session: AsyncSession,
    root_job_id: int,
    job_id: int,
    recipe_resolved_id: int,
) -> CraftJob:
    from app.db.models import CraftRecipeResolved

    job = await session.get(CraftJob, job_id)
    if job is None or job.root_id != root_job_id:
        raise ValueError("job not found")
    r = await session.get(CraftRecipeResolved, recipe_resolved_id)
    if r is None:
        raise ValueError("recipe not found")
    assert_transition_ok(job.state, "ready")
    job.state = "ready"
    job.chosen_nesql_recipe_id = r.nesql_recipe_id
    job.alternatives = None
    await session.commit()
    await session.refresh(job)
    return job


async def start_plan(session: AsyncSession, root_job_id: int, client_id: str | None) -> dict[str, Any]:
    job = await session.get(CraftJob, root_job_id)
    if job is None:
        raise ValueError("root job not found")
    if job.state not in ("ready",):
        raise ValueError("job not ready to start")

    m = (
        await session.execute(
            select(CraftAliasMember)
            .where(CraftAliasMember.alias_id == job.goal_alias_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if m is None:
        raise ValueError("alias has no members")

    name = await unlocal_name_for_nesql_item(m.nesql_item_id)
    if not name:
        name = "unknown"

    req = SimpleNamespace(
        item_name=name,
        item_damage=m.damage,
        amount=job.goal_amount,
        cpu_name=job.preferred_cpu,
        label=None,
    )
    command = build_request_command(req)  # type: ignore[arg-type]

    import uuid

    task_id = f"craft_{uuid.uuid4().hex[:12]}"
    await task_store.add(session, task_id, client_id, [command], READY)
    job.task_id = task_id
    assert_transition_ok(job.state, "programmed")
    job.state = "programmed"
    await session.commit()
    return {"task_id": task_id, "commands": [command]}


async def cancel_plan(session: AsyncSession, root_job_id: int) -> None:
    rows = (
        await session.execute(select(CraftJob).where(CraftJob.root_id == root_job_id))
    ).scalars().all()
    for j in rows:
        try:
            assert_transition_ok(j.state, "cancelled")
        except ValueError:
            continue
        j.state = "cancelled"
    await session.commit()
