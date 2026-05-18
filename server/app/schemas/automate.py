"""Pydantic schemas for /api/automate/*."""

from __future__ import annotations

from pydantic import BaseModel


class AddTriggerModel(BaseModel):
    name: str
    action: str
    trigger_kwargs: dict
    action_kwargs: dict
    interval: int | None = None


class TriggerRequestModel(BaseModel):
    trigger_task_id: str


class AddTimerModel(BaseModel):
    name: str
    action: str
    trigger_kwargs: dict
    action_kwargs: dict


class TimerRequestModel(BaseModel):
    timer_id: str
