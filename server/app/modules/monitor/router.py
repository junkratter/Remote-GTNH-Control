"""/api/monitor — Lapotron capacitor / energy monitoring (placeholder).

Currently only exposes `task history` for `monitor` task to keep the
existing `website/src/pages/Monitor.vue` working. Real-time logic lives
in `app/automation/callbacks.py::parse_capacitor_data` once a `monitor`
entry is added in `app/automation/config.py::timer_task_config`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import token_required
from app.core.tasks import task_store
from app.db.session import get_session
from app.schemas import StandardResponseModel


router = APIRouter(dependencies=[Depends(token_required)])


@router.get("/capacitor/history", response_model=StandardResponseModel)
async def capacitor_history(
    start_time: int | None = Query(None),
    end_time: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    history = await task_store.history(session, "monitor", start_time, end_time)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "task_id": "monitor",
            "history": history or [],
        },
    }
