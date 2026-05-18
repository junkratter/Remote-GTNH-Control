"""Schemas for /api/map."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BlockObservation(BaseModel):
    dimension: int = 0
    x: int
    y: int
    z: int
    block_name: str | None = None
    hardness: float | None = None
    fluid: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ScanReport(BaseModel):
    observations: list[BlockObservation]


class BlockOut(BlockObservation):
    id: int
    seen_at: str | None = None
