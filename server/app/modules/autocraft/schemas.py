"""Schemas for /api/autocraft."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ItemRef(BaseModel):
    name: str
    damage: int = 0
    amount: int = 1
    label: str | None = None


class PatternIn(BaseModel):
    interface_address: str = Field(..., description="UUID of ME Interface (analyzer)")
    slot: int = Field(..., ge=1, le=36)
    kind: Literal["crafting", "processing"] = "processing"
    inputs: list[ItemRef]
    outputs: list[ItemRef]
    label: str | None = None


class PatternOut(PatternIn):
    id: int


class CraftRequest(BaseModel):
    client_id: str
    item_name: str
    item_damage: int = 0
    amount: int = 1
    cpu_name: str | None = None
    label: str | None = None


class CraftRequestOut(BaseModel):
    id: int
    task_id: str | None
    state: str
