"""SQLAlchemy ORM models for remote-gtnh-control.

Tables:
    tasks               — OC long-poll task store (replaces tasks/*.json).
    task_histories      — append-only completed snapshots.
    devices             — OC clients seen on the wire.
    robots              — registered robot OC-clients with state machine.
    mining_jobs         — Phase 4: GT miner placements with status.
    power_jobs          — Phase 4b: GT generator / gas turbine + fuel capsules.
    autocraft_patterns  — Phase 3: programmed AE2 patterns.
    autocraft_requests  — Phase 3: queued craft requests.
    world_blocks        — Phase 5: ore/fluid scan results from geolyzer robots.
    quest_completions   — Phase 6: per-player quest completion (optional).
    craft_*             — Phase C: aliases, resolved recipes, plans, jobs (ADR-006).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


_JSON = JSON().with_variant(JSONB, "postgresql")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    commands: Mapped[list] = mapped_column(_JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True, default="ready")
    chunked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    results: Mapped[Optional[Any]] = mapped_column(_JSON, nullable=True)
    created_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    pending_time: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    completed_time: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))

    histories: Mapped[list["TaskHistory"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_tasks_status_created", "status", "created_time"),
        Index("idx_tasks_client_status", "client_id", "status"),
    )


class TaskHistory(Base):
    __tablename__ = "task_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    results: Mapped[Optional[Any]] = mapped_column(_JSON)
    created_time: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    pending_time: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    completed_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    task: Mapped[Task] = relationship(back_populates="histories")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    recent_activity: Mapped[list] = mapped_column(_JSON, default=list)


class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    label: Mapped[Optional[str]] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(32), default="idle", index=True)
    last_message: Mapped[Optional[str]] = mapped_column(Text)
    telemetry: Mapped[dict] = mapped_column(_JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class MiningJob(Base):
    __tablename__ = "mining_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    robot_client_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    miner_kind: Mapped[str] = mapped_column(String(32), default="advanced_miner")
    dimension: Mapped[int] = mapped_column(Integer, default=0)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    z: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    note: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PowerJob(Base):
    __tablename__ = "power_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    robot_client_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    generator_kind: Mapped[str] = mapped_column(String(48), default="advanced_combustion_generator")
    fuel_kind: Mapped[str] = mapped_column(String(32), default="diesel")
    capsule_count: Mapped[int] = mapped_column(Integer, default=4)
    dimension: Mapped[int] = mapped_column(Integer, default=0)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    z: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    note: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AutocraftPattern(Base):
    __tablename__ = "autocraft_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interface_address: Mapped[str] = mapped_column(String(64), index=True)
    slot: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16), default="processing")
    inputs: Mapped[list] = mapped_column(_JSON, default=list)
    outputs: Mapped[list] = mapped_column(_JSON, default=list)
    label: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_autocraft_patterns_iface_slot", "interface_address", "slot", unique=True),
    )


class AutocraftRequest(Base):
    __tablename__ = "autocraft_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64), index=True)
    item_name: Mapped[str] = mapped_column(String(128))
    item_damage: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[int] = mapped_column(Integer, default=1)
    cpu_name: Mapped[Optional[str]] = mapped_column(String(64))
    label: Mapped[Optional[str]] = mapped_column(String(255))
    task_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    state: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    result: Mapped[Optional[dict]] = mapped_column(_JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class WorldBlock(Base):
    __tablename__ = "world_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimension: Mapped[int] = mapped_column(Integer, index=True)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    z: Mapped[int] = mapped_column(Integer)
    block_name: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    hardness: Mapped[Optional[float]] = mapped_column(Float)
    fluid: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    meta: Mapped[dict] = mapped_column(_JSON, default=dict)
    seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_world_blocks_coords", "dimension", "x", "y", "z", unique=True),
        Index("ix_world_blocks_xz", "dimension", "x", "z"),
    )


class QuestCompletion(Base):
    __tablename__ = "quest_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player: Mapped[str] = mapped_column(String(64), index=True)
    nesql_quest_id: Mapped[int] = mapped_column(Integer, index=True)
    completed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_quest_completions_player_quest", "player", "nesql_quest_id", unique=True),
    )


# --- Craft domain (ADR-006) ---------------------------------------------------


class CraftAlias(Base):
    __tablename__ = "craft_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(256), index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CraftAliasMember(Base):
    __tablename__ = "craft_alias_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alias_id: Mapped[int] = mapped_column(
        ForeignKey("craft_aliases.id", ondelete="CASCADE"), index=True
    )
    nesql_item_id: Mapped[int] = mapped_column(Integer, index=True)
    damage: Mapped[int] = mapped_column(Integer, default=0)
    nbt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    preferred: Mapped[bool] = mapped_column(Boolean, default=False)


class CraftRecipeResolved(Base):
    __tablename__ = "craft_recipes_resolved"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nesql_recipe_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    machine: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    duration_ticks: Mapped[int] = mapped_column(Integer, default=0)
    eu_per_tick: Mapped[int] = mapped_column(Integer, default=0)
    hash_inputs: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    preferred_cpu: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class CraftRecipeInput(Base):
    __tablename__ = "craft_recipe_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("craft_recipes_resolved.id", ondelete="CASCADE"), index=True
    )
    slot: Mapped[int] = mapped_column(Integer, default=0)
    alias_id: Mapped[int] = mapped_column(ForeignKey("craft_aliases.id"), index=True)
    fluid_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, default=1)
    required: Mapped[bool] = mapped_column(Boolean, default=True)


class CraftRecipeOutput(Base):
    __tablename__ = "craft_recipe_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("craft_recipes_resolved.id", ondelete="CASCADE"), index=True
    )
    slot: Mapped[int] = mapped_column(Integer, default=0)
    alias_id: Mapped[int] = mapped_column(ForeignKey("craft_aliases.id"), index=True)
    fluid_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, default=1)
    chance_ppm: Mapped[int] = mapped_column(Integer, default=1_000_000)

    __table_args__ = (Index("ix_craft_recipe_outputs_alias", "alias_id"),)


class CraftResolvedSnapshot(Base):
    """Singleton row ``id=1``: last ``build_resolved`` stats for ``GET /api/craft/health``."""

    __tablename__ = "craft_resolved_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    built_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    recipe_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)


class CraftPlan(Base):
    __tablename__ = "craft_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    root_job_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    plan_json: Mapped[dict] = mapped_column(_JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))


class CraftJob(Base):
    __tablename__ = "craft_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("craft_jobs.id"), nullable=True)
    root_id: Mapped[int] = mapped_column(Integer, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("craft_plans.id", ondelete="CASCADE"), index=True)
    goal_alias_id: Mapped[int] = mapped_column(ForeignKey("craft_aliases.id"), index=True)
    goal_amount: Mapped[int] = mapped_column(Integer, default=1)
    chosen_nesql_recipe_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_cpu: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="planning", index=True)
    missing: Mapped[Optional[dict]] = mapped_column(_JSON, nullable=True)
    alternatives: Mapped[Optional[list]] = mapped_column(_JSON, nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    __table_args__ = (
        Index("ix_craft_jobs_state_created", "state", "created_at"),
        Index("ix_craft_jobs_root", "root_id"),
        Index("ix_craft_jobs_client_state", "client_id", "state"),
    )
