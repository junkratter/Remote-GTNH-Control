"""Add composite task indexes for claim/dispatch hot paths.

Revision ID: 0003_task_perf
Revises: 0002_power
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect


revision: str = "0003_task_perf"
down_revision: str | None = "0002_power_jobs"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _index_exists(bind, name: str, table: str) -> bool:
    insp = inspect(bind)
    return any(ix.get("name") == name for ix in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    if not _index_exists(bind, "idx_tasks_status_created", "tasks"):
        op.create_index(
            "idx_tasks_status_created", "tasks", ["status", "created_time"], unique=False
        )
    if not _index_exists(bind, "idx_tasks_client_status", "tasks"):
        op.create_index(
            "idx_tasks_client_status", "tasks", ["client_id", "status"], unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _index_exists(bind, "idx_tasks_client_status", "tasks"):
        op.drop_index("idx_tasks_client_status", table_name="tasks")
    if _index_exists(bind, "idx_tasks_status_created", "tasks"):
        op.drop_index("idx_tasks_status_created", table_name="tasks")
