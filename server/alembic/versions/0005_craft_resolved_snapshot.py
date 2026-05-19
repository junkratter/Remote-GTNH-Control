"""Craft resolved graph snapshot metadata (health / freshness).

Revision ID: 0005_craft_snapshot
Revises: 0004_craft_domain
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0005_craft_snapshot"
down_revision: str | None = "0004_craft_domain"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "craft_resolved_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("built_at", sa.DateTime(timezone=True)),
        sa.Column("recipe_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edge_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        sa.text(
            "INSERT INTO craft_resolved_snapshot (id, built_at, recipe_count, edge_count) "
            "VALUES (1, NULL, 0, 0)"
        )
    )


def downgrade() -> None:
    op.drop_table("craft_resolved_snapshot")
