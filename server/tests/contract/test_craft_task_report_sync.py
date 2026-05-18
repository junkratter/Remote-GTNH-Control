"""Craft ``craft_*`` task reports update ``craft_jobs`` (gap plan §7).

The route ``POST /api/task/report`` delegates to
:func:`app.modules.craft.sync_report.sync_craft_job_after_report`; this test
targets that function directly to avoid env/session ordering issues in the
session-scoped ASGI app fixture.
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.core.constants import READY
from app.core.tasks import task_store
from app.db.models import CraftAlias, CraftJob, CraftPlan
from app.db.session import AsyncSessionLocal
from app.modules.craft.sync_report import sync_craft_job_after_report


@pytest.mark.asyncio
async def test_sync_craft_job_after_report_marks_done() -> None:
    tid = f"craft_{uuid.uuid4().hex[:12]}"
    alias_key = f"contract_alias_{uuid.uuid4().hex[:10]}"

    async with AsyncSessionLocal() as session:
        alias = CraftAlias(key=alias_key, source="manual", priority=0)
        session.add(alias)
        await session.flush()
        plan = CraftPlan(plan_json={}, status="open", client_id=None)
        session.add(plan)
        await session.flush()
        job = CraftJob(
            parent_id=None,
            root_id=0,
            plan_id=plan.id,
            goal_alias_id=alias.id,
            goal_amount=1,
            state="programmed",
            task_id=tid,
            client_id="oc",
        )
        session.add(job)
        await session.flush()
        job.root_id = job.id
        job_id = job.id
        await task_store.add(session, tid, "oc", ["return 1"], READY)

    results = [json.dumps({"message": "success", "data": {}})]
    async with AsyncSessionLocal() as session:
        await sync_craft_job_after_report(session, tid, results, None)

    async with AsyncSessionLocal() as session:
        job2 = await session.get(CraftJob, job_id)
    assert job2 is not None
    assert job2.state == "done"
