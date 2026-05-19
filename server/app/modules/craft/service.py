"""Craft service — plans, lifecycle."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
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
from app.modules.craft.oc_commands import bulk_program_lua
from app.modules.craft.patterns import recipe_has_matching_pattern
from app.modules.craft.state_machine import assert_transition_ok
from app.modules.craft.stock_store import load_alias_stock_map


def normalize_client_id(raw: str | None) -> str | None:
    """Normalize OC ``client_id`` (for example ``01`` becomes ``client_01``)."""

    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    if re.fullmatch(r"\d+", s):
        return f"client_{s}"
    return s


async def create_plan(
    session: AsyncSession,
    *,
    goal_alias_id: int,
    amount: int,
    client_id: str | None,
    app: Any | None = None,
    ae_stock_client_id: str | None = None,
) -> tuple[CraftPlan, CraftJob, dict[str, Any]]:
    cid = normalize_client_id(client_id)
    sid = normalize_client_id(ae_stock_client_id)
    stock_client = sid if sid else cid
    stock = await load_alias_stock_map(app, session, stock_client) if app else {}

    plan, job, pj = await solver.build_recursive_plan(
        session,
        goal_alias_id=goal_alias_id,
        goal_amount=amount,
        client_id=cid,
        stock=stock,
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
        await session.execute(
            select(CraftJob).where(CraftJob.root_id == job.root_id).order_by(CraftJob.id)
        )
    ).scalars().all()

    jobs_out = []
    for j in children:
        jobs_out.append(
            {
                "id": j.id,
                "parent_id": j.parent_id,
                "root_id": j.root_id,
                "state": j.state,
                "goal_alias_id": j.goal_alias_id,
                "goal_amount": j.goal_amount,
                "chosen_nesql_recipe_id": j.chosen_nesql_recipe_id,
                "task_id": j.task_id,
                "alternatives": j.alternatives,
                "missing": j.missing,
                "error": j.error,
            }
        )

    return {"plan": plan.plan_json, "jobs": jobs_out}


async def choose_alternative(
    session: AsyncSession,
    root_job_id: int,
    job_id: int,
    recipe_resolved_id: int,
    *,
    app: Any | None = None,
) -> CraftJob:
    job = await session.get(CraftJob, job_id)
    if job is None or job.root_id != root_job_id:
        raise ValueError("job not found")
    if job.state != "awaiting_choice":
        raise ValueError("job is not awaiting_choice")

    plan = await session.get(CraftPlan, job.plan_id)
    stock_client = normalize_client_id(plan.client_id if plan else None)
    stock = await load_alias_stock_map(app, session, stock_client) if app else {}

    await solver.expand_job_after_choice(
        session,
        job,
        recipe_resolved_pk=recipe_resolved_id,
        stock=stock,
    )

    await solver.refresh_plan_summary_for_root(session, root_job_id)
    await session.commit()
    await session.refresh(job)
    return job


def _jobs_post_order(session_rows: list[CraftJob]) -> list[CraftJob]:
    by_parent: dict[int | None, list[CraftJob]] = defaultdict(list)
    for j in session_rows:
        by_parent[j.parent_id].append(j)

    for lst in by_parent.values():
        lst.sort(key=lambda x: x.id)

    root_job = next((j for j in session_rows if j.parent_id is None), None)
    if root_job is None:
        return []

    ordered: list[CraftJob] = []

    def dfs(n: CraftJob) -> None:
        for ch in by_parent.get(n.id, []):
            dfs(ch)
        ordered.append(n)

    dfs(root_job)
    return ordered


async def start_plan(session: AsyncSession, root_job_id: int, client_id: str | None) -> dict[str, Any]:
    cid = normalize_client_id(client_id)

    rows = (
        await session.execute(select(CraftJob).where(CraftJob.root_id == root_job_id))
    ).scalars().all()
    if not rows:
        raise ValueError("root job not found")

    ordered = _jobs_post_order(list(rows))
    to_run = [j for j in ordered if j.state == "ready"]

    if not to_run:
        raise ValueError("no ready jobs to start")

    task_payload: list[dict[str, Any]] = []

    for job in to_run:
        m = (
            await session.execute(
                select(CraftAliasMember)
                .where(CraftAliasMember.alias_id == job.goal_alias_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if m is None:
            raise ValueError(f"alias has no members (job {job.id})")

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

        task_id = f"craft_{uuid.uuid4().hex[:12]}"
        await task_store.add(session, task_id, cid, [command], READY)
        job.task_id = task_id
        assert_transition_ok(job.state, "programmed")
        job.state = "programmed"
        task_payload.append({"job_id": job.id, "task_id": task_id, "commands": [command]})

    await solver.refresh_plan_summary_for_root(session, root_job_id)
    await session.commit()

    first = task_payload[0]
    return {
        "task_id": first["task_id"],
        "commands": first["commands"],
        "tasks": task_payload,
    }


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
    await solver.refresh_plan_summary_for_root(session, root_job_id)
    await session.commit()


async def craft_health_snapshot(session: AsyncSession) -> dict[str, Any]:
    from sqlalchemy import func

    from app.db.models import CraftAlias, CraftRecipeResolved, CraftResolvedSnapshot

    aliases_n = await session.scalar(select(func.count()).select_from(CraftAlias))
    resolved_n = await session.scalar(select(func.count()).select_from(CraftRecipeResolved))
    snap = await session.get(CraftResolvedSnapshot, 1)
    return {
        "craft_aliases": int(aliases_n or 0),
        "craft_recipes_resolved": int(resolved_n or 0),
        "resolved_graph_built_at": snap.built_at.isoformat() if snap and snap.built_at else None,
        "resolved_graph_recipe_count": snap.recipe_count if snap else None,
        "resolved_graph_edge_count": snap.edge_count if snap else None,
    }


async def enqueue_plan_patterns(
    session: AsyncSession,
    *,
    root_job_id: int,
    client_id: str | None,
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """Program ME slots via ``ae.bulkProgramPatterns`` for jobs stuck in ``awaiting_pattern``."""

    cid = normalize_client_id(client_id)
    if not cid:
        raise ValueError("client_id is required")
    if not patterns:
        raise ValueError("patterns required")

    jobs = (
        await session.execute(
            select(CraftJob).where(
                CraftJob.root_id == root_job_id,
                CraftJob.state == "awaiting_pattern",
            )
        )
    ).scalars().all()
    if not jobs:
        raise ValueError("no awaiting_pattern jobs under this plan")

    lua = bulk_program_lua(patterns)
    task_id = f"craftpat_{uuid.uuid4().hex[:12]}"
    await task_store.add(session, task_id, cid, [lua], READY)

    for j in jobs:
        assert_transition_ok(j.state, "programmed")
        j.state = "programmed"
        j.task_id = task_id

    await solver.refresh_plan_summary_for_root(session, root_job_id)
    await session.commit()
    return {"task_id": task_id, "jobs_updated": [j.id for j in jobs]}


async def promote_blocked_parent(session: AsyncSession, parent_id: int | None) -> None:
    """If all children are terminal, unblock parent (``blocked`` → ``ready`` / ``awaiting_pattern``)."""

    if parent_id is None:
        return

    parent = await session.get(CraftJob, parent_id)
    if parent is None or parent.state != "blocked":
        return

    kids = (
        await session.execute(select(CraftJob).where(CraftJob.parent_id == parent_id))
    ).scalars().all()
    if not kids:
        return

    terminal = {"done", "failed", "cancelled"}
    if not all(k.state in terminal for k in kids):
        return

    if any(k.state == "failed" for k in kids):
        assert_transition_ok(parent.state, "failed")
        parent.state = "failed"
        parent.error = parent.error or "child_failed"
        await session.flush()
        await solver.refresh_plan_summary_for_root(session, parent.root_id)
        await promote_blocked_parent(session, parent.parent_id)
        return

    if any(k.state == "cancelled" for k in kids):
        try:
            assert_transition_ok(parent.state, "cancelled")
            parent.state = "cancelled"
        except ValueError:
            pass
        await session.flush()
        await solver.refresh_plan_summary_for_root(session, parent.root_id)
        await promote_blocked_parent(session, parent.parent_id)
        return

    nesql_rid = parent.chosen_nesql_recipe_id
    if nesql_rid is None:
        return

    ok = await recipe_has_matching_pattern(session, nesql_rid)
    if ok:
        assert_transition_ok(parent.state, "ready")
        parent.state = "ready"
    else:
        assert_transition_ok(parent.state, "awaiting_pattern")
        parent.state = "awaiting_pattern"
        parent.missing = {"reason": "no_me_pattern", "nesql_recipe_id": nesql_rid}

    await session.flush()
    await solver.refresh_plan_summary_for_root(session, parent.root_id)
    await promote_blocked_parent(session, parent.parent_id)
