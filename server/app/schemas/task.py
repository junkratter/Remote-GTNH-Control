"""Pydantic schemas used by /api/task/*."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CommandResultModel(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    results: list[str] = Field(..., description="Per-command result strings")


class CommandChunkedResultModel(BaseModel):
    task_id: str
    results: list[Any]


class AddCommandModel(BaseModel):
    task_id: str | None = None
    commands: list[str] = Field(..., description="Lua commands to execute on OC")
    client_id: str | None = None


class AddTaskByNameModel(BaseModel):
    task_id: str = Field(..., description="Name of task in automation config")
    client_id: str | None = None


class AddTaskResponseModel(BaseModel):
    task_id: str
    message: str


class TaskStatusResponseModel(BaseModel):
    task_id: str
    status: str
    results: list[str] | None = None


class TaskHistoryItemModel(BaseModel):
    results: Any | None = None
    created_time: str | None = None
    pending_time: str | None = None
    completed_time: str | None = None


class TaskHistoryResponseModel(BaseModel):
    task_id: str
    total: int
    history: list[TaskHistoryItemModel]
