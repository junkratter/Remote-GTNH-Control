"""power_jobs — GT generator / gas turbine deployment queue

Revision ID: 0002_power_jobs
Revises: 0001_initial
Create Date: 2026-05-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_power_jobs"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "power_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("robot_client_id", sa.String(length=64)),
        sa.Column("generator_kind", sa.String(length=48), nullable=False),
        sa.Column("fuel_kind", sa.String(length=32), nullable=False),
        sa.Column("capsule_count", sa.Integer(), nullable=False, server_default="4"),
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
    op.create_index("ix_power_jobs_robot_client_id", "power_jobs", ["robot_client_id"])
    op.create_index("ix_power_jobs_state", "power_jobs", ["state"])


def downgrade() -> None:
    op.drop_index("ix_power_jobs_state", table_name="power_jobs")
    op.drop_index("ix_power_jobs_robot_client_id", table_name="power_jobs")
    op.drop_table("power_jobs")
