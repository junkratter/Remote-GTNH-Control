"""initial schema (tasks, devices, robots, autocraft, world_blocks, quests)

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-16 21:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("client_id", sa.String(length=64)),
        sa.Column("commands", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("chunked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("results", sa.JSON()),
        sa.Column("created_time", sa.DateTime(timezone=True)),
        sa.Column("pending_time", sa.DateTime(timezone=True)),
        sa.Column("completed_time", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_tasks_client_id", "tasks", ["client_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    op.create_table(
        "task_histories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=128), sa.ForeignKey("tasks.id", ondelete="CASCADE")),
        sa.Column("results", sa.JSON()),
        sa.Column("created_time", sa.DateTime(timezone=True)),
        sa.Column("pending_time", sa.DateTime(timezone=True)),
        sa.Column("completed_time", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_histories_task_id", "task_histories", ["task_id"])

    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("first_seen", sa.DateTime(timezone=True)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("recent_activity", sa.JSON()),
    )

    op.create_table(
        "robots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=128)),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("last_message", sa.Text()),
        sa.Column("telemetry", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("client_id", name="uq_robots_client_id"),
    )
    op.create_index("ix_robots_client_id", "robots", ["client_id"])
    op.create_index("ix_robots_kind", "robots", ["kind"])
    op.create_index("ix_robots_state", "robots", ["state"])

    op.create_table(
        "mining_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("robot_client_id", sa.String(length=64)),
        sa.Column("miner_kind", sa.String(length=32)),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("z", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_mining_jobs_robot_client_id", "mining_jobs", ["robot_client_id"])
    op.create_index("ix_mining_jobs_state", "mining_jobs", ["state"])

    op.create_table(
        "autocraft_patterns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("interface_address", sa.String(length=64), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("label", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_autocraft_patterns_iface_slot",
        "autocraft_patterns",
        ["interface_address", "slot"],
        unique=True,
    )

    op.create_table(
        "autocraft_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("item_name", sa.String(length=128), nullable=False),
        sa.Column("item_damage", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("cpu_name", sa.String(length=64)),
        sa.Column("label", sa.String(length=255)),
        sa.Column("task_id", sa.String(length=128)),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_autocraft_requests_client_id", "autocraft_requests", ["client_id"])
    op.create_index("ix_autocraft_requests_state", "autocraft_requests", ["state"])
    op.create_index("ix_autocraft_requests_task_id", "autocraft_requests", ["task_id"])

    op.create_table(
        "world_blocks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("z", sa.Integer(), nullable=False),
        sa.Column("block_name", sa.String(length=128)),
        sa.Column("hardness", sa.Float()),
        sa.Column("fluid", sa.String(length=64)),
        sa.Column("meta", sa.JSON()),
        sa.Column("seen_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_world_blocks_coords",
        "world_blocks",
        ["dimension", "x", "y", "z"],
        unique=True,
    )
    op.create_index("ix_world_blocks_xz", "world_blocks", ["dimension", "x", "z"])
    op.create_index("ix_world_blocks_dimension", "world_blocks", ["dimension"])
    op.create_index("ix_world_blocks_block_name", "world_blocks", ["block_name"])
    op.create_index("ix_world_blocks_fluid", "world_blocks", ["fluid"])

    op.create_table(
        "quest_completions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("player", sa.String(length=64), nullable=False),
        sa.Column("nesql_quest_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_quest_completions_player_quest",
        "quest_completions",
        ["player", "nesql_quest_id"],
        unique=True,
    )
    op.create_index("ix_quest_completions_player", "quest_completions", ["player"])
    op.create_index("ix_quest_completions_nesql_quest_id", "quest_completions", ["nesql_quest_id"])


def downgrade() -> None:
    op.drop_table("quest_completions")
    op.drop_table("world_blocks")
    op.drop_table("autocraft_requests")
    op.drop_table("autocraft_patterns")
    op.drop_table("mining_jobs")
    op.drop_table("robots")
    op.drop_table("devices")
    op.drop_table("task_histories")
    op.drop_table("tasks")
