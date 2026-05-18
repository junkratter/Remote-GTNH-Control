"""/api/map — geolyzer scan results + lookup (Phase 5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import token_required
from app.db.models import WorldBlock
from app.db.session import get_session
from app.modules.worldmap.schemas import BlockObservation, BlockOut, ScanReport
from app.schemas import StandardResponseModel


router = APIRouter(dependencies=[Depends(token_required)])


def _to_out(row: WorldBlock) -> BlockOut:
    return BlockOut(
        id=row.id,
        dimension=row.dimension,
        x=row.x,
        y=row.y,
        z=row.z,
        block_name=row.block_name,
        hardness=row.hardness,
        fluid=row.fluid,
        meta=row.meta or {},
        seen_at=row.seen_at.isoformat() if row.seen_at else None,
    )


@router.post("/scan", response_model=StandardResponseModel)
async def submit_scan(payload: ScanReport, session: AsyncSession = Depends(get_session)) -> dict:
    """Idempotent upsert of observations: PK is (dimension, x, y, z)."""

    accepted = 0
    for obs in payload.observations:
        stmt = sqlite_insert(WorldBlock).values(
            dimension=obs.dimension,
            x=obs.x,
            y=obs.y,
            z=obs.z,
            block_name=obs.block_name,
            hardness=obs.hardness,
            fluid=obs.fluid,
            meta=obs.meta,
            seen_at=func.datetime("now"),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["dimension", "x", "y", "z"],
            set_={
                "block_name": stmt.excluded.block_name,
                "hardness": stmt.excluded.hardness,
                "fluid": stmt.excluded.fluid,
                "meta": stmt.excluded.meta,
                "seen_at": func.datetime("now"),
            },
        )
        await session.execute(stmt)
        accepted += 1
    await session.commit()
    return {"code": 200, "message": "success", "data": {"accepted": accepted}}


@router.get("/blocks", response_model=StandardResponseModel)
async def list_blocks(
    dimension: int = 0,
    x_min: int | None = Query(None),
    x_max: int | None = Query(None),
    z_min: int | None = Query(None),
    z_max: int | None = Query(None),
    block_name: str | None = Query(None),
    fluid: str | None = Query(None),
    limit: int = Query(5000, le=20000),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(WorldBlock).where(WorldBlock.dimension == dimension)
    if x_min is not None:
        stmt = stmt.where(WorldBlock.x >= x_min)
    if x_max is not None:
        stmt = stmt.where(WorldBlock.x <= x_max)
    if z_min is not None:
        stmt = stmt.where(WorldBlock.z >= z_min)
    if z_max is not None:
        stmt = stmt.where(WorldBlock.z <= z_max)
    if block_name:
        stmt = stmt.where(WorldBlock.block_name == block_name)
    if fluid:
        stmt = stmt.where(WorldBlock.fluid == fluid)
    stmt = stmt.limit(limit)

    rows = await session.execute(stmt)
    return {
        "code": 200,
        "message": "success",
        "data": [_to_out(r).model_dump() for r in rows.scalars().all()],
    }
