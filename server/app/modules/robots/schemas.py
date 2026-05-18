"""Pydantic schemas for /api/robots."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RobotRegister(BaseModel):
    client_id: str = Field(..., description="OC env.clientId")
    kind: str = Field(..., description="ae | crop | miner | power | scanner | generic")
    label: str | None = None


class RobotUpdate(BaseModel):
    state: str | None = None
    last_message: str | None = None
    telemetry: dict[str, Any] | None = None


class RobotOut(BaseModel):
    id: int
    client_id: str
    kind: str
    label: str | None
    state: str
    last_message: str | None
    telemetry: dict[str, Any]


class MiningJobCreate(BaseModel):
    robot_client_id: str | None = None
    miner_kind: str = "advanced_miner"
    dimension: int = 0
    x: int
    y: int
    z: int
    note: str | None = None


class MiningJobPatch(BaseModel):
    state: str | None = None
    note: str | None = None
    robot_client_id: str | None = None


class MiningJobOut(BaseModel):
    id: int
    robot_client_id: str | None
    miner_kind: str
    dimension: int
    x: int
    y: int
    z: int
    state: str
    note: str | None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class PowerJobCreate(BaseModel):
    robot_client_id: str | None = None
    generator_kind: str = "advanced_combustion_generator"
    fuel_kind: str = "diesel"
    capsule_count: int = Field(4, ge=1, le=64)
    dimension: int = 0
    x: int
    y: int
    z: int
    note: str | None = None


class PowerJobPatch(BaseModel):
    state: str | None = None
    note: str | None = None
    robot_client_id: str | None = None


class PowerJobOut(BaseModel):
    id: int
    robot_client_id: str | None
    generator_kind: str
    fuel_kind: str
    capsule_count: int
    dimension: int
    x: int
    y: int
    z: int
    state: str
    note: str | None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
