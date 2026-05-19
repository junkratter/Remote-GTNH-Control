"""Recursive craft planner (ADR-006 §5).

Expands resolved recipes into a ``CraftJob`` tree with AE-aware pruning when a
Redis-backed inventory snapshot exists for ``ae_stock_client_id``.
"""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CraftAlias,
    CraftAliasMember,
    CraftJob,
    CraftPlan,
    CraftRecipeInput,
    CraftRecipeOutput,
    CraftRecipeResolved,
)
from app.modules.craft import patterns as craft_patterns
from app.modules.craft.state_machine import assert_transition_ok


CRAFT_MAX_DEPTH = 28


async def _recipes_for_goal(session: AsyncSession, alias_id: int) -> list[CraftRecipeResolved]:
    rows = (
        await session.execute(
            select(CraftRecipeResolved)
            .join(
                CraftRecipeOutput,
                CraftRecipeOutput.recipe_id == CraftRecipeResolved.id,
            )
            .where(CraftRecipeOutput.alias_id == alias_id)
            .distinct()
        )
    ).scalars().all()

    def rank(r: CraftRecipeResolved) -> tuple[int, int, int]:
        return (int(r.eu_per_tick or 0), int(r.duration_ticks or 0), int(r.nesql_recipe_id))

    return sorted(rows, key=rank)


async def _output_amount(session: AsyncSession, resolved_recipe_pk: int, alias_id: int) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(CraftRecipeOutput.amount), 0)).where(
            CraftRecipeOutput.recipe_id == resolved_recipe_pk,
            CraftRecipeOutput.alias_id == alias_id,
        )
    )
    return int(total or 0)


async def _sorted_inputs(session: AsyncSession, resolved_recipe_pk: int) -> list[CraftRecipeInput]:
    rows = (
        await session.execute(
            select(CraftRecipeInput)
            .where(CraftRecipeInput.recipe_id == resolved_recipe_pk)
            .order_by(CraftRecipeInput.slot)
        )
    ).scalars().all()
    return list(rows)


async def _materialize_recipe_branch(
    session: AsyncSession,
    job: CraftJob,
    recipe_row: CraftRecipeResolved,
    *,
    ancestor_goals: frozenset[int],
    depth: int,
    stock: dict[int, int],
    client_id: str | None,
) -> None:
    goal_alias_id = job.goal_alias_id
    goal_amount = job.goal_amount

    out_amt = await _output_amount(session, recipe_row.id, goal_alias_id)
    if out_amt <= 0:
        out_amt = 1
    crafts_needed = max(1, math.ceil(goal_amount / out_amt))

    inputs = await _sorted_inputs(session, recipe_row.id)

    next_ancestors = ancestor_goals | {goal_alias_id}
    child_failed = False
    any_child = False

    for inp in inputs:
        if inp.fluid_id or not inp.required:
            continue
        need = int(inp.amount or 1) * crafts_needed
        av = int(stock.get(inp.alias_id, 0))
        use = min(need, av)
        stock[inp.alias_id] = av - use
        residual = need - use
        if residual <= 0:
            continue
        any_child = True
        child = await _spawn_goal_job(
            session,
            plan_id=job.plan_id,
            parent_id=job.id,
            goal_alias_id=inp.alias_id,
            goal_amount=residual,
            client_id=client_id,
            stock=stock,
            ancestor_goals=next_ancestors,
            depth=depth + 1,
            root_id=job.root_id,
        )
        if child.state == "failed":
            child_failed = True

    if child_failed:
        assert_transition_ok(job.state, "failed")
        job.state = "failed"
        job.error = job.error or "child_failed"
        return

    if any_child:
        assert_transition_ok(job.state, "blocked")
        job.state = "blocked"
        return

    ok_pat = await craft_patterns.recipe_has_matching_pattern(session, recipe_row.nesql_recipe_id)
    if ok_pat:
        assert_transition_ok(job.state, "ready")
        job.state = "ready"
    else:
        assert_transition_ok(job.state, "awaiting_pattern")
        job.state = "awaiting_pattern"
        job.missing = {"reason": "no_me_pattern", "nesql_recipe_id": recipe_row.nesql_recipe_id}


async def _spawn_goal_job(
    session: AsyncSession,
    *,
    plan_id: int,
    parent_id: int | None,
    goal_alias_id: int,
    goal_amount: int,
    client_id: str | None,
    stock: dict[int, int],
    ancestor_goals: frozenset[int],
    depth: int,
    root_id: int,
) -> CraftJob:
    if depth > CRAFT_MAX_DEPTH:
        job = CraftJob(
            parent_id=parent_id,
            root_id=root_id,
            plan_id=plan_id,
            goal_alias_id=goal_alias_id,
            goal_amount=goal_amount,
            state="failed",
            error="depth_exceeded",
            client_id=client_id,
        )
        session.add(job)
        await session.flush()
        return job

    if goal_alias_id in ancestor_goals:
        job = CraftJob(
            parent_id=parent_id,
            root_id=root_id,
            plan_id=plan_id,
            goal_alias_id=goal_alias_id,
            goal_amount=goal_amount,
            state="failed",
            error="cycle_detected",
            client_id=client_id,
        )
        session.add(job)
        await session.flush()
        return job

    recipes = await _recipes_for_goal(session, goal_alias_id)
    if not recipes:
        job = CraftJob(
            parent_id=parent_id,
            root_id=root_id,
            plan_id=plan_id,
            goal_alias_id=goal_alias_id,
            goal_amount=goal_amount,
            state="failed",
            error="no_recipe_for_alias",
            client_id=client_id,
        )
        session.add(job)
        await session.flush()
        return job

    if len(recipes) >= 2:
        alts = [{"recipe_id": r.id, "nesql_recipe_id": r.nesql_recipe_id} for r in recipes[:8]]
        job = CraftJob(
            parent_id=parent_id,
            root_id=root_id,
            plan_id=plan_id,
            goal_alias_id=goal_alias_id,
            goal_amount=goal_amount,
            state="awaiting_choice",
            alternatives=alts,
            chosen_nesql_recipe_id=None,
            client_id=client_id,
        )
        session.add(job)
        await session.flush()
        return job

    recipe = recipes[0]
    job = CraftJob(
        parent_id=parent_id,
        root_id=root_id,
        plan_id=plan_id,
        goal_alias_id=goal_alias_id,
        goal_amount=goal_amount,
        state="planning",
        chosen_nesql_recipe_id=recipe.nesql_recipe_id,
        client_id=client_id,
    )
    session.add(job)
    await session.flush()

    await _materialize_recipe_branch(
        session,
        job,
        recipe,
        ancestor_goals=ancestor_goals,
        depth=depth,
        stock=stock,
        client_id=client_id,
    )
    return job


async def compute_plan_summary(session: AsyncSession, plan_row: CraftPlan, root_job: CraftJob) -> dict[str, Any]:
    jobs = (
        await session.execute(select(CraftJob).where(CraftJob.plan_id == plan_row.id))
    ).scalars().all()

    states = [j.state for j in jobs]
    summary_counts: dict[str, int] = {}
    for s in states:
        summary_counts[s] = summary_counts.get(s, 0) + 1

    stage = root_job.state
    err = root_job.error if root_job.state == "failed" else None
    if any(j.state == "awaiting_choice" for j in jobs):
        stage = "awaiting_choice"
    elif any(j.state == "failed" for j in jobs):
        stage = "failed"
        if err is None:
            failed_jobs = [j for j in jobs if j.state == "failed"]
            err = failed_jobs[0].error if failed_jobs else "failed"

    chosen_rid = root_job.chosen_nesql_recipe_id
    chosen_pk = None
    if chosen_rid is not None:
        rid_row = await session.scalar(
            select(CraftRecipeResolved.id).where(CraftRecipeResolved.nesql_recipe_id == chosen_rid)
        )
        chosen_pk = int(rid_row) if rid_row is not None else None

    return {
        "goal_alias_id": root_job.goal_alias_id,
        "goal_amount": root_job.goal_amount,
        "stage": stage,
        "root_job_id": root_job.id,
        "plan_id": plan_row.id,
        "chosen_recipe_id": chosen_pk,
        "chosen_nesql_recipe_id": chosen_rid,
        "error": err,
        "job_counts": summary_counts,
    }


async def build_recursive_plan(
    session: AsyncSession,
    *,
    goal_alias_id: int,
    goal_amount: int,
    client_id: str | None,
    stock: dict[int, int] | None = None,
) -> tuple[CraftPlan, CraftJob, dict[str, Any]]:
    """Create ``CraftPlan`` + recursive job tree."""

    stock_use = dict(stock or {})

    plan_row = CraftPlan(plan_json={}, status="open", client_id=client_id)
    session.add(plan_row)
    await session.flush()

    root = CraftJob(
        parent_id=None,
        root_id=0,
        plan_id=plan_row.id,
        goal_alias_id=goal_alias_id,
        goal_amount=goal_amount,
        state="planning",
        client_id=client_id,
    )
    session.add(root)
    await session.flush()

    anc: frozenset[int] = frozenset()

    recipes = await _recipes_for_goal(session, goal_alias_id)
    if not recipes:
        root.root_id = root.id
        root.state = "failed"
        root.error = "no_recipe_for_alias"
        plan_row.root_job_id = root.id
        pj = await compute_plan_summary(session, plan_row, root)
        plan_row.plan_json = pj
        return plan_row, root, pj

    if len(recipes) >= 2:
        alts = [{"recipe_id": r.id, "nesql_recipe_id": r.nesql_recipe_id} for r in recipes[:8]]
        root.root_id = root.id
        root.state = "awaiting_choice"
        root.alternatives = alts
        root.chosen_nesql_recipe_id = None
        plan_row.root_job_id = root.id
        pj = await compute_plan_summary(session, plan_row, root)
        plan_row.plan_json = pj
        return plan_row, root, pj

    recipe = recipes[0]
    root.root_id = root.id
    root.chosen_nesql_recipe_id = recipe.nesql_recipe_id
    await _materialize_recipe_branch(
        session,
        root,
        recipe,
        ancestor_goals=anc,
        depth=0,
        stock=stock_use,
        client_id=client_id,
    )

    plan_row.root_job_id = root.id
    pj = await compute_plan_summary(session, plan_row, root)
    plan_row.plan_json = pj
    return plan_row, root, pj


async def expand_job_after_choice(
    session: AsyncSession,
    job: CraftJob,
    *,
    recipe_resolved_pk: int,
    stock: dict[int, int] | None,
) -> CraftJob:
    """Expand branches after POST ``/choose`` (recipe_row is ``craft_recipes_resolved.id``)."""

    r = await session.get(CraftRecipeResolved, recipe_resolved_pk)
    if r is None:
        raise ValueError("recipe not found")

    job.chosen_nesql_recipe_id = r.nesql_recipe_id
    job.alternatives = None

    ancestor_goals: set[int] = set()
    depth = 0
    cur_id = job.parent_id
    while cur_id:
        depth += 1
        parent = await session.get(CraftJob, cur_id)
        if parent is None:
            break
        ancestor_goals.add(parent.goal_alias_id)
        cur_id = parent.parent_id

    stock_use = dict(stock or {})

    await _materialize_recipe_branch(
        session,
        job,
        r,
        ancestor_goals=frozenset(ancestor_goals),
        depth=depth,
        stock=stock_use,
        client_id=job.client_id,
    )

    plan_row = await session.get(CraftPlan, job.plan_id)
    root_job = await session.get(CraftJob, job.root_id)
    if plan_row is not None and root_job is not None:
        plan_row.plan_json = await compute_plan_summary(session, plan_row, root_job)

    return job


async def refresh_plan_summary_for_root(session: AsyncSession, root_job_id: int) -> None:
    root = await session.get(CraftJob, root_job_id)
    if root is None:
        return
    plan_row = await session.get(CraftPlan, root.plan_id)
    if plan_row is None:
        return
    plan_row.plan_json = await compute_plan_summary(session, plan_row, root)


# --- Alias helpers (unchanged API) -------------------------------------------


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


# Legacy name kept for imports elsewhere
build_minimal_plan = build_recursive_plan
