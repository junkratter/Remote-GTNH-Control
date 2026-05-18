"""/api/craft/* — planner plans and alias helpers (ADR-006)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import token_required
from app.db.models import CraftAlias
from app.db.session import get_session
from app.modules.craft import service
from app.modules.events.notify import notify
from app.modules.craft.schemas import (
    CraftAliasOut,
    CraftChooseIn,
    CraftManualAliasIn,
    CraftPlanCreate,
    CraftPlanResponse,
    CraftStartIn,
    CraftStartResponse,
    CraftTreeResponse,
)
from app.schemas import StandardResponseModel

router = APIRouter(prefix="/craft", tags=["craft"], dependencies=[Depends(token_required)])


def _ok(data: object) -> dict:
    return {"code": 200, "message": "success", "data": data}


@router.post("/plan", response_model=StandardResponseModel)
async def create_plan(
    request: Request,
    body: CraftPlanCreate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        plan, job, pj = await service.create_plan(
            session,
            goal_alias_id=body.goal_alias_id,
            amount=body.amount,
            client_id=body.client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await notify(
        request.app,
        "craft",
        {
            "kind": "plan_created",
            "plan_id": plan.id,
            "root_job_id": job.id,
            "state": job.state,
        },
    )
    return _ok(
        CraftPlanResponse(
            plan_json=pj,
            root_job_id=job.id,
            state=job.state,
        ).model_dump()
    )


@router.get("/plan/{root_job_id}", response_model=StandardResponseModel)
async def get_plan(
    root_job_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tree = await service.get_plan_tree(session, root_job_id)
    if tree is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _ok(CraftTreeResponse(**tree).model_dump())


@router.post("/plan/{root_job_id}/choose", response_model=StandardResponseModel)
async def choose_alternative(
    request: Request,
    root_job_id: int,
    body: CraftChooseIn,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        job = await service.choose_alternative(
            session,
            root_job_id=root_job_id,
            job_id=body.job_id,
            recipe_resolved_id=body.recipe_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await notify(
        request.app,
        "craft",
        {"kind": "choice", "root_job_id": root_job_id, "job_id": job.id, "state": job.state},
    )
    return _ok({"id": job.id, "state": job.state})


@router.post("/plan/{root_job_id}/start", response_model=StandardResponseModel)
async def start_plan(
    request: Request,
    root_job_id: int,
    body: CraftStartIn,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        out = await service.start_plan(session, root_job_id, body.client_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await notify(
        request.app,
        "craft",
        {"kind": "start", "root_job_id": root_job_id, "task_id": out.get("task_id")},
    )
    return _ok(CraftStartResponse(**out).model_dump())


@router.post("/plan/{root_job_id}/cancel", response_model=StandardResponseModel)
async def cancel_plan(
    root_job_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await service.cancel_plan(session, root_job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await notify(request.app, "craft", {"kind": "cancel", "root_job_id": root_job_id})
    return _ok({"root_job_id": root_job_id})


@router.get("/aliases", response_model=StandardResponseModel)
async def list_aliases(
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = await session.execute(select(CraftAlias).order_by(CraftAlias.id.desc()).limit(limit))
    rows = q.scalars().all()
    return _ok(
        [
            CraftAliasOut(
                id=r.id, key=r.key, source=r.source, priority=r.priority
            ).model_dump()
            for r in rows
        ]
    )


@router.post("/aliases", response_model=StandardResponseModel)
async def create_manual_alias(
    body: CraftManualAliasIn,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.db.models import CraftAliasMember

    existing = (
        await session.execute(select(CraftAlias).where(CraftAlias.key == body.key))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="alias key already exists")

    alias = CraftAlias(key=body.key, source="manual", priority=0)
    session.add(alias)
    await session.flush()
    for m in body.members:
        session.add(
            CraftAliasMember(
                alias_id=alias.id,
                nesql_item_id=m.nesql_item_id,
                damage=m.damage,
                weight=m.weight,
                preferred=m.preferred,
            )
        )
    await session.commit()
    await session.refresh(alias)
    return _ok(
        CraftAliasOut(
            id=alias.id, key=alias.key, source=alias.source, priority=alias.priority
        ).model_dump()
    )
