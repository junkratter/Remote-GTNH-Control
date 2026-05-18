"""Shared response envelope."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class StandardResponseModel(BaseModel, Generic[T]):
    """Envelope `{code, message, data}` used by every endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    code: int = Field(..., description="Business code; 200 means success.")
    message: str = Field(..., description="Human-readable status text.")
    data: Any | None = Field(None, description="Payload (shape varies per route).")
