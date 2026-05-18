"""/api/robots — registry + state-machine + mining-job queue."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import token_required
from app.db.models import MiningJob, PowerJob
from app.db.session import get_session
from app.modules.robots import service
from app.modules.robots.schemas import (
    MiningJobCreate,
    MiningJobOut,
    MiningJobPatch,
    PowerJobCreate,
    PowerJobOut,
    PowerJobPatch,
    RobotOut,
    RobotRegister,
    RobotUpdate,
)
from app.schemas import StandardResponseModel


router = APIRouter(dependencies=[Depends(token_required)])


def _serialize_robot(robot) -> RobotOut:
    return RobotOut(
        id=robot.id,
        client_id=robot.client_id,
        kind=robot.kind,
        label=robot.label,
        state=robot.state,
        last_message=robot.last_message,
        telemetry=robot.telemetry or {},
    )


def _serialize_power_job(job: PowerJob) -> PowerJobOut:
    return PowerJobOut(
        id=job.id,
        robot_client_id=job.robot_client_id,
        generator_kind=job.generator_kind,
        fuel_kind=job.fuel_kind,
        capsule_count=job.capsule_count,
        dimension=job.dimension,
        x=job.x,
        y=job.y,
        z=job.z,
        state=job.state,
        note=job.note,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _serialize_job(job: MiningJob) -> MiningJobOut:
    return MiningJobOut(
        id=job.id,
        robot_client_id=job.robot_client_id,
        miner_kind=job.miner_kind,
        dimension=job.dimension,
        x=job.x,
        y=job.y,
        z=job.z,
        state=job.state,
        note=job.note,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.post("/register", response_model=StandardResponseModel)
async def register_robot(
    payload: RobotRegister, session: AsyncSession = Depends(get_session)
) -> dict:
    robot = await service.upsert_robot(
        session,
        client_id=payload.client_id,
        kind=payload.kind,
        label=payload.label,
    )
    return {"code": 200, "message": "success", "data": _serialize_robot(robot).model_dump()}


@router.get("/list", response_model=StandardResponseModel)
async def list_robots(session: AsyncSession = Depends(get_session)) -> dict:
    robots = await service.list_robots(session)
    return {
        "code": 200,
        "message": "success",
        "data": [_serialize_robot(r).model_dump() for r in robots],
    }


# ---------------------------------------------------------------------------
# Mining / power jobs — MUST be before /{client_id}/state (static paths).
# ---------------------------------------------------------------------------


@router.post("/mining-jobs", response_model=StandardResponseModel)
async def create_mining_job(
    payload: MiningJobCreate,
    enqueue: bool = Query(True, description="Queue acceptJob on the robot via /api/task/add"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    job = await service.create_mining_job(
        session,
        robot_client_id=payload.robot_client_id,
        miner_kind=payload.miner_kind,
        dimension=payload.dimension,
        x=payload.x,
        y=payload.y,
        z=payload.z,
        note=payload.note,
    )
    if enqueue and job.robot_client_id:
        queued = await service.enqueue_mining_job_task(session, job, deploy=False)
        if queued is not None:
            job = queued
    return {"code": 200, "message": "success", "data": _serialize_job(job).model_dump()}


@router.get("/mining-jobs", response_model=StandardResponseModel)
async def list_mining_jobs(session: AsyncSession = Depends(get_session)) -> dict:
    jobs = await service.list_mining_jobs(session)
    return {
        "code": 200,
        "message": "success",
        "data": [_serialize_job(j).model_dump() for j in jobs],
    }


@router.get("/mining-jobs/next", response_model=StandardResponseModel)
async def next_mining_job(
    robot_client_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    job = await service.next_pending_job_for_robot(session, robot_client_id)
    if job is None:
        return {"code": 200, "message": "success", "data": None}
    return {"code": 200, "message": "success", "data": _serialize_job(job).model_dump()}


@router.post("/mining-jobs/{job_id}/enqueue", response_model=StandardResponseModel)
async def enqueue_mining_job(
    job_id: int,
    deploy: bool = Query(False, description="Queue deploy (acceptJob + placeForward)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    job = await service.get_mining_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Mining job not found")
    queued = await service.enqueue_mining_job_task(session, job, deploy=deploy)
    if queued is None:
        raise HTTPException(status_code=400, detail="Mining job has no robot_client_id")
    return {"code": 200, "message": "success", "data": _serialize_job(queued).model_dump()}


@router.patch("/mining-jobs/{job_id}", response_model=StandardResponseModel)
async def patch_mining_job(
    job_id: int,
    payload: MiningJobPatch,
    session: AsyncSession = Depends(get_session),
) -> dict:
    job = await service.patch_mining_job(
        session,
        job_id,
        state=payload.state,
        note=payload.note,
        robot_client_id=payload.robot_client_id,
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Mining job not found")
    return {"code": 200, "message": "success", "data": _serialize_job(job).model_dump()}


@router.post("/power-jobs", response_model=StandardResponseModel)
async def create_power_job(
    payload: PowerJobCreate, session: AsyncSession = Depends(get_session)
) -> dict:
    job = await service.create_power_job(
        session,
        robot_client_id=payload.robot_client_id,
        generator_kind=payload.generator_kind,
        fuel_kind=payload.fuel_kind,
        capsule_count=payload.capsule_count,
        dimension=payload.dimension,
        x=payload.x,
        y=payload.y,
        z=payload.z,
        note=payload.note,
    )
    return {
        "code": 200,
        "message": "success",
        "data": _serialize_power_job(job).model_dump(),
    }


@router.get("/power-jobs", response_model=StandardResponseModel)
async def list_power_jobs(session: AsyncSession = Depends(get_session)) -> dict:
    jobs = await service.list_power_jobs(session)
    return {
        "code": 200,
        "message": "success",
        "data": [_serialize_power_job(j).model_dump() for j in jobs],
    }


@router.get("/power-jobs/next", response_model=StandardResponseModel)
async def next_power_job(
    robot_client_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    job = await service.next_pending_power_job_for_robot(session, robot_client_id)
    if job is None:
        return {"code": 200, "message": "success", "data": None}
    return {
        "code": 200,
        "message": "success",
        "data": _serialize_power_job(job).model_dump(),
    }


@router.patch("/power-jobs/{job_id}", response_model=StandardResponseModel)
async def patch_power_job(
    job_id: int,
    payload: PowerJobPatch,
    session: AsyncSession = Depends(get_session),
) -> dict:
    job = await service.patch_power_job(
        session,
        job_id,
        state=payload.state,
        note=payload.note,
        robot_client_id=payload.robot_client_id,
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Power job not found")
    return {
        "code": 200,
        "message": "success",
        "data": _serialize_power_job(job).model_dump(),
    }


@router.post("/{client_id}/state", response_model=StandardResponseModel)
async def update_state(
    client_id: str,
    payload: RobotUpdate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    robot = await service.update_state(
        session,
        client_id=client_id,
        state=payload.state,
        last_message=payload.last_message,
        telemetry=payload.telemetry,
    )
    if robot is None:
        raise HTTPException(status_code=404, detail="Robot not registered")
    return {"code": 200, "message": "success", "data": _serialize_robot(robot).model_dump()}
