"""/api/info/* — server metadata."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.auth import token_required
from app.core.devices import device_manager
from app.db.session import get_session
from app.schemas import StandardResponseModel


router = APIRouter()


@router.get(
    "/meta",
    response_model=StandardResponseModel,
    dependencies=[Depends(token_required)],
)
async def get_meta(session: AsyncSession = Depends(get_session)) -> StandardResponseModel:
    return StandardResponseModel(
        code=200,
        message="success",
        data={
            "version": __version__,
            "device_num": await device_manager.count(session),
        },
    )


@router.get("/version", response_model=StandardResponseModel)
async def get_version() -> StandardResponseModel:
    return StandardResponseModel(code=200, message="success", data={"version": __version__})


@router.get(
    "/devices",
    response_model=StandardResponseModel,
    dependencies=[Depends(token_required)],
)
async def get_devices(session: AsyncSession = Depends(get_session)) -> StandardResponseModel:
    return StandardResponseModel(
        code=200,
        message="success",
        data=await device_manager.list(session),
    )
