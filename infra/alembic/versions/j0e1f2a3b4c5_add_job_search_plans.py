"""add job-search plans and tasks

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-08-03
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j0e1f2a3b4c5"
down_revision: Union[str, None] = "i9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_search_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("jd_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="generating"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("weekly_hours", sa.SmallInteger(), nullable=True),
        sa.Column("supplemental_background", sa.Text(), nullable=True),
        sa.Column(
            "input_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("generation_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generation_error", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('generating', 'regenerating', 'active', 'completed', 'failed')", name="ck_plan_status"
        ),
        sa.CheckConstraint("weekly_hours IS NULL OR weekly_hours BETWEEN 1 AND 80", name="ck_plan_weekly_hours"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["match_result_id"], ["jd_match_results.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plans_user_updated", "job_search_plans", ["user_id", "updated_at"])
    op.create_index("ix_plans_user_status", "job_search_plans", ["user_id", "status"])
    op.create_index(
        "uq_active_plan_jd_resume",
        "job_search_plans",
        ["jd_id", "resume_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('generating', 'regenerating', 'active', 'failed')"),
    )

    op.create_table(
        "job_search_plan_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "basis",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="todo"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "category IN ('gap_priority', 'resume', 'skill', 'evidence_project', 'interview', 'application_review')",
            name="ck_plan_task_category",
        ),
        sa.CheckConstraint("source IN ('ai', 'manual')", name="ck_plan_task_source"),
        sa.CheckConstraint("priority IN ('high', 'medium', 'low')", name="ck_plan_task_priority"),
        sa.CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="ck_plan_task_status"),
        sa.ForeignKeyConstraint(["plan_id"], ["job_search_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_tasks_plan_order", "job_search_plan_tasks", ["plan_id", "sort_order"])
    op.create_index("ix_plan_tasks_plan_status", "job_search_plan_tasks", ["plan_id", "status"])
    op.create_index("ix_plan_tasks_due_date", "job_search_plan_tasks", ["due_date"])


def downgrade() -> None:
    op.drop_index("ix_plan_tasks_due_date", table_name="job_search_plan_tasks")
    op.drop_index("ix_plan_tasks_plan_status", table_name="job_search_plan_tasks")
    op.drop_index("ix_plan_tasks_plan_order", table_name="job_search_plan_tasks")
    op.drop_table("job_search_plan_tasks")
    op.drop_index("uq_active_plan_jd_resume", table_name="job_search_plans")
    op.drop_index("ix_plans_user_status", table_name="job_search_plans")
    op.drop_index("ix_plans_user_updated", table_name="job_search_plans")
    op.drop_table("job_search_plans")
