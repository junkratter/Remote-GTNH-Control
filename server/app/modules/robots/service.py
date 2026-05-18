"""Robot state machine + persistence helpers.

The robots themselves don't have push capability, so the server is the
source of truth: it accepts updates from periodic OC reports and stores
the latest state.

State machine valid transitions (light validation, easy to extend):

    idle      -> moving | working | error
    moving    -> working | unloading | error
    working   -> unloading | error
    unloading -> returning | error
    returning -> idle | error
    error     -> idle           (after manual reset)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MiningJobState, PowerJobState, READY, RobotState
from app.core.logging import logger
from app.core.tasks import task_store
from app.db.models import MiningJob, PowerJob, Robot


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    RobotState.IDLE: {RobotState.MOVING, RobotState.WORKING, RobotState.ERROR},
    RobotState.MOVING: {RobotState.WORKING, RobotState.UNLOADING, RobotState.ERROR},
    RobotState.WORKING: {RobotState.UNLOADING, RobotState.ERROR, RobotState.IDLE},
    RobotState.UNLOADING: {RobotState.RETURNING, RobotState.ERROR, RobotState.IDLE},
    RobotState.RETURNING: {RobotState.IDLE, RobotState.ERROR},
    RobotState.ERROR: {RobotState.IDLE},
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def upsert_robot(
    session: AsyncSession,
    *,
    client_id: str,
    kind: str,
    label: str | None,
) -> Robot:
    existing = (
        await session.execute(select(Robot).where(Robot.client_id == client_id))
    ).scalar_one_or_none()
    if existing is None:
        robot = Robot(client_id=client_id, kind=kind, label=label, state=RobotState.IDLE)
        session.add(robot)
    else:
        existing.kind = kind
        existing.label = label
        robot = existing
    await session.commit()
    return robot


async def update_state(
    session: AsyncSession,
    *,
    client_id: str,
    state: str | None,
    last_message: str | None,
    telemetry: dict | None,
) -> Robot | None:
    robot = (
        await session.execute(select(Robot).where(Robot.client_id == client_id))
    ).scalar_one_or_none()
    if robot is None:
        return None
    if state is not None:
        allowed = ALLOWED_TRANSITIONS.get(robot.state, set())
        if state != robot.state and state not in allowed:
            logger.warning(
                "robot %s: illegal transition %s -> %s (allowed: %s)",
                client_id,
                robot.state,
                state,
                sorted(allowed),
            )
        robot.state = state
    if last_message is not None:
        robot.last_message = last_message
    if telemetry is not None:
        merged = dict(robot.telemetry or {})
        merged.update(telemetry)
        robot.telemetry = merged
    await session.commit()
    return robot


async def list_robots(session: AsyncSession) -> list[Robot]:
    rows = await session.execute(select(Robot))
    return list(rows.scalars().all())


# --- Mining jobs (GT miner queue) --------------------------------------------


async def create_mining_job(
    session: AsyncSession,
    *,
    robot_client_id: str | None,
    miner_kind: str,
    dimension: int,
    x: int,
    y: int,
    z: int,
    note: str | None,
) -> MiningJob:
    job = MiningJob(
        robot_client_id=robot_client_id,
        miner_kind=miner_kind,
        dimension=dimension,
        x=x,
        y=y,
        z=z,
        note=note,
        state=MiningJobState.PENDING,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def list_mining_jobs(session: AsyncSession) -> list[MiningJob]:
    rows = await session.execute(select(MiningJob).order_by(MiningJob.created_at.desc()))
    return list(rows.scalars().all())


async def get_mining_job(session: AsyncSession, job_id: int) -> MiningJob | None:
    row = await session.execute(select(MiningJob).where(MiningJob.id == job_id))
    return row.scalar_one_or_none()


async def next_pending_job_for_robot(
    session: AsyncSession, robot_client_id: str
) -> MiningJob | None:
    """Oldest pending job assigned to this robot client."""

    row = await session.execute(
        select(MiningJob)
        .where(
            MiningJob.state == MiningJobState.PENDING,
            MiningJob.robot_client_id == robot_client_id,
        )
        .order_by(MiningJob.id.asc())
        .limit(1)
    )
    return row.scalar_one_or_none()


def _lua_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def mining_job_accept_command(job: MiningJob) -> str:
    mk = _lua_escape(job.miner_kind or "advanced_miner")
    return (
        f"return robot_miner.acceptJob({{ job_id={job.id}, x={job.x}, y={job.y}, "
        f"z={job.z}, dim={job.dimension}, miner_kind=\"{mk}\" }})"
    )


def mining_job_deploy_command(job: MiningJob) -> str:
    mk = _lua_escape(job.miner_kind or "advanced_miner")
    return (
        f"return robot_miner.deploy({{ job_id={job.id}, x={job.x}, y={job.y}, "
        f"z={job.z}, dim={job.dimension}, miner_kind=\"{mk}\", miner_slot=1 }})"
    )


async def enqueue_mining_job_task(
    session: AsyncSession,
    job: MiningJob,
    *,
    deploy: bool = False,
) -> MiningJob | None:
    """Put acceptJob/deploy on the OC task queue for this job's robot."""

    if not job.robot_client_id:
        return job

    task_id = f"mining_job_{job.id}"
    command = mining_job_deploy_command(job) if deploy else mining_job_accept_command(job)
    await task_store.add(session, task_id, job.robot_client_id, [command], READY)
    updated = await patch_mining_job(session, job.id, state=MiningJobState.RUNNING, note=None, robot_client_id=None)
    logger.info(
        "queued mining job %s for %s (deploy=%s, task_id=%s)",
        job.id,
        job.robot_client_id,
        deploy,
        task_id,
    )
    return updated


async def patch_mining_job(
    session: AsyncSession,
    job_id: int,
    *,
    state: str | None,
    note: str | None,
    robot_client_id: str | None,
) -> MiningJob | None:
    job = await get_mining_job(session, job_id)
    if job is None:
        return None
    if robot_client_id is not None:
        job.robot_client_id = robot_client_id
    if note is not None:
        job.note = note
    if state is not None:
        job.state = state
        if state == MiningJobState.RUNNING and job.started_at is None:
            job.started_at = _utcnow()
        if state in (MiningJobState.DONE, MiningJobState.FAILED):
            job.finished_at = _utcnow()
    await session.commit()
    await session.refresh(job)
    return job


# --- Power jobs (generator / gas turbine + fuel) -------------------------------


async def create_power_job(
    session: AsyncSession,
    *,
    robot_client_id: str | None,
    generator_kind: str,
    fuel_kind: str,
    capsule_count: int,
    dimension: int,
    x: int,
    y: int,
    z: int,
    note: str | None,
) -> PowerJob:
    job = PowerJob(
        robot_client_id=robot_client_id,
        generator_kind=generator_kind,
        fuel_kind=fuel_kind,
        capsule_count=capsule_count,
        dimension=dimension,
        x=x,
        y=y,
        z=z,
        note=note,
        state=PowerJobState.PENDING,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def list_power_jobs(session: AsyncSession) -> list[PowerJob]:
    rows = await session.execute(select(PowerJob).order_by(PowerJob.created_at.desc()))
    return list(rows.scalars().all())


async def get_power_job(session: AsyncSession, job_id: int) -> PowerJob | None:
    row = await session.execute(select(PowerJob).where(PowerJob.id == job_id))
    return row.scalar_one_or_none()


async def next_pending_power_job_for_robot(
    session: AsyncSession, robot_client_id: str
) -> PowerJob | None:
    row = await session.execute(
        select(PowerJob)
        .where(
            PowerJob.state == PowerJobState.PENDING,
            PowerJob.robot_client_id == robot_client_id,
        )
        .order_by(PowerJob.id.asc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def patch_power_job(
    session: AsyncSession,
    job_id: int,
    *,
    state: str | None,
    note: str | None,
    robot_client_id: str | None,
) -> PowerJob | None:
    job = await get_power_job(session, job_id)
    if job is None:
        return None
    if robot_client_id is not None:
        job.robot_client_id = robot_client_id
    if note is not None:
        job.note = note
    if state is not None:
        job.state = state
        if state == PowerJobState.RUNNING and job.started_at is None:
            job.started_at = _utcnow()
        if state in (PowerJobState.DONE, PowerJobState.FAILED):
            job.finished_at = _utcnow()
    await session.commit()
    await session.refresh(job)
    return job
