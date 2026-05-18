"""/api/autocraft — pattern programming + craft queue (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import token_required
from app.core.tasks import task_store
from app.db.models import AutocraftPattern, AutocraftRequest
from app.db.session import get_session
from app.modules.autocraft import service
from app.modules.autocraft.schemas import (
    CraftRequest,
    CraftRequestOut,
    PatternIn,
    PatternOut,
)
from app.schemas import StandardResponseModel


router = APIRouter(dependencies=[Depends(token_required)])


def _ok(data) -> dict:
    return {"code": 200, "message": "success", "data": data}


def _pattern_to_out(pattern: AutocraftPattern) -> PatternOut:
    return PatternOut(
        id=pattern.id,
        interface_address=pattern.interface_address,
        slot=pattern.slot,
        kind=pattern.kind,
        inputs=pattern.inputs or [],
        outputs=pattern.outputs or [],
        label=pattern.label,
    )


def _request_to_dict(r: AutocraftRequest) -> dict:
    return {
        "id": r.id,
        "client_id": r.client_id,
        "item_name": r.item_name,
        "item_damage": r.item_damage,
        "amount": r.amount,
        "cpu_name": r.cpu_name,
        "label": r.label,
        "state": r.state,
        "task_id": r.task_id,
        "result": r.result,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# --- patterns ---------------------------------------------------------------


@router.get("/patterns", response_model=StandardResponseModel)
async def list_patterns(session: AsyncSession = Depends(get_session)) -> dict:
    rows = await session.execute(select(AutocraftPattern).order_by(AutocraftPattern.id))
    items = rows.scalars().all()
    return _ok([_pattern_to_out(p).model_dump() for p in items])


@router.post("/patterns", response_model=StandardResponseModel)
async def upsert_pattern(payload: PatternIn, session: AsyncSession = Depends(get_session)) -> dict:
    stmt = (
        select(AutocraftPattern)
        .where(AutocraftPattern.interface_address == payload.interface_address)
        .where(AutocraftPattern.slot == payload.slot)
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    inputs = [i.model_dump() for i in payload.inputs]
    outputs = [o.model_dump() for o in payload.outputs]
    if existing is None:
        pattern = AutocraftPattern(
            interface_address=payload.interface_address,
            slot=payload.slot,
            kind=payload.kind,
            inputs=inputs,
            outputs=outputs,
            label=payload.label,
        )
        session.add(pattern)
    else:
        existing.kind = payload.kind
        existing.inputs = inputs
        existing.outputs = outputs
        existing.label = payload.label
        pattern = existing
    await session.commit()
    return _ok(_pattern_to_out(pattern).model_dump())


@router.delete("/patterns/{pattern_id}", response_model=StandardResponseModel)
async def delete_pattern(pattern_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    pattern = await session.get(AutocraftPattern, pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    await session.delete(pattern)
    await session.commit()
    return _ok({"id": pattern_id})


@router.post("/patterns/{pattern_id}/program", response_model=StandardResponseModel)
async def program_pattern(
    pattern_id: int,
    client_id: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Enqueue an OC task that programs the pattern into the ME Interface."""

    pattern = await session.get(AutocraftPattern, pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    commands = service.build_pattern_commands(pattern)
    task_id = f"pattern_{pattern.id}"
    await task_store.add(session, task_id=task_id, client_id=client_id, commands=commands)
    return _ok({"task_id": task_id, "commands": commands})


# --- craft requests ---------------------------------------------------------


@router.post("/request", response_model=StandardResponseModel)
async def request_craft(payload: CraftRequest, session: AsyncSession = Depends(get_session)) -> dict:
    req = AutocraftRequest(
        client_id=payload.client_id,
        item_name=payload.item_name,
        item_damage=payload.item_damage,
        amount=payload.amount,
        cpu_name=payload.cpu_name,
        label=payload.label,
        state="queued",
    )
    session.add(req)
    await session.commit()
    task_id = await service.enqueue_craft(session, req)
    return _ok(CraftRequestOut(id=req.id, task_id=task_id, state=req.state).model_dump())


@router.get("/requests", response_model=StandardResponseModel)
async def list_requests(
    state: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(AutocraftRequest).order_by(AutocraftRequest.created_at.desc())
    if state:
        stmt = stmt.where(AutocraftRequest.state == state)
    stmt = stmt.limit(limit)
    rows = await session.execute(stmt)
    return _ok([_request_to_dict(r) for r in rows.scalars().all()])


@router.get("/requests/{request_id}", response_model=StandardResponseModel)
async def get_request(request_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    req = await session.get(AutocraftRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Craft request not found")
    return _ok(_request_to_dict(req))


@router.post("/requests/{request_id}/cancel", response_model=StandardResponseModel)
async def cancel_request(request_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    req = await session.get(AutocraftRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Craft request not found")
    task_id = await service.enqueue_cancel(session, req)
    if task_id is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel: request was not bound to a named CPU",
        )
    return _ok({"task_id": task_id, "request": _request_to_dict(req)})


# --- CPU monitoring ---------------------------------------------------------


@router.post("/cpus/scan", response_model=StandardResponseModel)
async def scan_cpus(
    client_id: str = Body(..., embed=True),
    detail: bool = Body(False, embed=True),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Enqueue `ae.getCpuList(detail)` on the chosen client.

    The client posts the JSON-encoded result back via `/api/task/report`;
    use `/api/task/status?task_id=...` to fetch it.
    """

    task_id = await service.enqueue_cpu_scan(session, client_id, detail=detail)
    return _ok({"task_id": task_id})
