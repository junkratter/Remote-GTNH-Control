"""Craft domain tables (ADR-006).

Revision ID: 0004_craft_domain
Revises: 0003_task_perf
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0004_craft_domain"
down_revision: str | None = "0003_task_perf"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = JSONB if is_pg else sa.JSON

    op.create_table(
        "craft_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(256), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_craft_aliases_key", "craft_aliases", ["key"])
    op.create_index("ix_craft_aliases_source", "craft_aliases", ["source"])

    op.create_table(
        "craft_alias_members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("alias_id", sa.Integer(), sa.ForeignKey("craft_aliases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nesql_item_id", sa.Integer(), nullable=False),
        sa.Column("damage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nbt_hash", sa.String(64)),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("preferred", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_craft_alias_members_alias_id", "craft_alias_members", ["alias_id"])
    op.create_index("ix_craft_alias_members_nesql_item_id", "craft_alias_members", ["nesql_item_id"])

    op.create_table(
        "craft_recipes_resolved",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nesql_recipe_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("machine", sa.String(128)),
        sa.Column("duration_ticks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eu_per_tick", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hash_inputs", sa.String(128)),
        sa.Column("preferred_cpu", sa.String(64)),
    )
    op.create_index("ix_craft_recipes_resolved_nesql_recipe_id", "craft_recipes_resolved", ["nesql_recipe_id"])

    op.create_table(
        "craft_recipe_inputs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("craft_recipes_resolved.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alias_id", sa.Integer(), sa.ForeignKey("craft_aliases.id"), nullable=False),
        sa.Column("fluid_id", sa.Integer()),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_craft_recipe_inputs_recipe_id", "craft_recipe_inputs", ["recipe_id"])
    op.create_index("ix_craft_recipe_inputs_alias_id", "craft_recipe_inputs", ["alias_id"])

    op.create_table(
        "craft_recipe_outputs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("craft_recipes_resolved.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alias_id", sa.Integer(), sa.ForeignKey("craft_aliases.id"), nullable=False),
        sa.Column("fluid_id", sa.Integer()),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("chance_ppm", sa.Integer(), nullable=False, server_default="1000000"),
    )
    op.create_index("ix_craft_recipe_outputs_recipe_id", "craft_recipe_outputs", ["recipe_id"])
    op.create_index("ix_craft_recipe_outputs_alias_id", "craft_recipe_outputs", ["alias_id"])

    op.create_table(
        "craft_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("root_job_id", sa.Integer()),
        sa.Column("plan_json", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(32), nullable=False, server_default="'open'"),
        sa.Column("client_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_craft_plans_root_job_id", "craft_plans", ["root_job_id"])
    op.create_index("ix_craft_plans_status", "craft_plans", ["status"])
    op.create_index("ix_craft_plans_client_id", "craft_plans", ["client_id"])

    op.create_table(
        "craft_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("craft_jobs.id")),
        sa.Column("root_id", sa.Integer(), nullable=False),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("craft_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("goal_alias_id", sa.Integer(), sa.ForeignKey("craft_aliases.id"), nullable=False),
        sa.Column("goal_amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("chosen_nesql_recipe_id", sa.Integer()),
        sa.Column("preferred_cpu", sa.String(64)),
        sa.Column("state", sa.String(32), nullable=False, server_default="'planning'"),
        sa.Column("missing", json_type),
        sa.Column("alternatives", json_type),
        sa.Column("client_id", sa.String(64)),
        sa.Column("task_id", sa.String(128)),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_craft_jobs_root_id", "craft_jobs", ["root_id"])
    op.create_index("ix_craft_jobs_plan_id", "craft_jobs", ["plan_id"])
    op.create_index("ix_craft_jobs_goal_alias_id", "craft_jobs", ["goal_alias_id"])
    op.create_index("ix_craft_jobs_state_created", "craft_jobs", ["state", "created_at"])
    op.create_index("ix_craft_jobs_client_state", "craft_jobs", ["client_id", "state"])
    op.create_index("ix_craft_jobs_task_id", "craft_jobs", ["task_id"])


def downgrade() -> None:
    op.drop_table("craft_jobs")
    op.drop_table("craft_plans")
    op.drop_table("craft_recipe_outputs")
    op.drop_table("craft_recipe_inputs")
    op.drop_table("craft_recipes_resolved")
    op.drop_table("craft_alias_members")
    op.drop_table("craft_aliases")
