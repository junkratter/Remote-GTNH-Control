"""Mirror OC ``craft_*`` task results into ``craft_jobs``."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CraftJob
from app.modules.autocraft.service import infer_craft_request_outcome
from app.modules.craft.state_machine import assert_transition_ok


async def sync_craft_job_after_report(
    session: AsyncSession,
    task_id: str,
    results: Any,
    app: Any | None = None,
) -> None:
    stmt = select(CraftJob).where(CraftJob.task_id == task_id).limit(1)
    job = (await session.execute(stmt)).scalar_one_or_none()
    if job is None:
        return

    oc_state, blob = infer_craft_request_outcome(results)
    if oc_state == "done":
        assert_transition_ok(job.state, "done")
        job.state = "done"
    else:
        assert_transition_ok(job.state, "failed")
        job.state = "failed"
        job.error = str(blob)[:2000]
    await session.commit()
    if app is not None:
        from app.modules.events.notify import notify

        await notify(
            app,
            "craft",
            {
                "kind": "task_report",
                "task_id": task_id,
                "job_id": job.id,
                "root_id": job.root_id,
                "state": job.state,
            },
        )
