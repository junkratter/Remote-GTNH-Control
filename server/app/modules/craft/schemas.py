"""Pydantic I/O for the craft domain (ADR-006)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CraftPlanCreate(BaseModel):
    goal_alias_id: int = Field(..., ge=1)
    amount: int = Field(..., ge=1, le=1_000_000)
    client_id: str | None = Field(None, max_length=64)
    ae_stock_client_id: str | None = Field(
        None,
        max_length=64,
        description="OC client whose Redis AE snapshot feeds planner pruning (defaults to ``client_id``).",
    )


class CraftChooseIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: int = Field(..., ge=1)
    recipe_id: int = Field(..., ge=1, description="``craft_recipes_resolved.id``")


class CraftStartIn(BaseModel):
    client_id: str | None = Field(None, max_length=64)


class CraftPlanResponse(BaseModel):
    plan_json: dict[str, Any]
    root_job_id: int
    state: str


class CraftTreeResponse(BaseModel):
    plan: dict[str, Any]
    jobs: list[dict[str, Any]]


class CraftStartTaskOut(BaseModel):
    job_id: int
    task_id: str
    commands: list[str]


class CraftStartResponse(BaseModel):
    task_id: str
    commands: list[str]
    tasks: list[CraftStartTaskOut] = Field(default_factory=list)


class CraftResolveAliasOut(BaseModel):
    alias_id: int


class CraftEnqueuePatternsIn(BaseModel):
    client_id: str = Field(..., max_length=64)
    patterns: list[dict[str, Any]] = Field(..., min_length=1)


class CraftManualAliasMemberIn(BaseModel):
    nesql_item_id: int
    damage: int = 0
    weight: int = 1
    preferred: bool = False


class CraftManualAliasIn(BaseModel):
    key: str = Field(..., max_length=256)
    members: list[CraftManualAliasMemberIn] = Field(default_factory=list)


class CraftAliasOut(BaseModel):
    id: int
    key: str
    source: str
    priority: int
