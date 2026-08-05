"""Add match_assessments for version-pinned match-v1 assessments (RIP-013 #109).

Revision ID: t4e5f6a7b8c9
Revises: s3d4e5f6a7b8
Create Date: 2026-08-05

Create the version-pinned Match Assessment aggregate with immutable
completion, active-run uniqueness, and safe failure state.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "t4e5f6a7b8c9"
down_revision: Union[str, None] = "s3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_targets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "jd_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_description_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "resume_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resume_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("policy_version", sa.String(50), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("dimension_scores", postgresql.JSONB(), nullable=True),
        sa.Column("rule_results", postgresql.JSONB(), nullable=True),
        sa.Column("gaps", postgresql.JSONB(), nullable=True),
        sa.Column("evidence_summary", postgresql.JSONB(), nullable=True),
        sa.Column("caps_applied", postgresql.JSONB(), nullable=True),
        sa.Column("recommendation", sa.String(30), nullable=True),
        sa.Column("score_before_caps", sa.Numeric(5, 2), nullable=True),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("overall_confidence", sa.Numeric(5, 3), nullable=True),
        sa.Column("model_name", sa.String(200), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("schema_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'evaluating', 'completed', 'failed')",
            name="ck_match_assessments_status",
        ),
        sa.CheckConstraint(
            "score_before_caps IS NULL OR (score_before_caps >= 0 AND score_before_caps <= 100)",
            name="ck_match_assessments_score_before_caps",
        ),
        sa.CheckConstraint(
            "total_score IS NULL OR (total_score >= 0 AND total_score <= 100)",
            name="ck_match_assessments_total_score",
        ),
        sa.CheckConstraint(
            "overall_confidence IS NULL OR (overall_confidence >= 0 AND overall_confidence <= 1)",
            name="ck_match_assessments_overall_confidence",
        ),
        sa.Index("ix_match_assessments_target", "job_target_id"),
        sa.Index("ix_match_assessments_jd_version", "jd_version_id"),
        sa.Index("ix_match_assessments_resume_version", "resume_version_id"),
        sa.Index(
            "ix_match_assessments_target_created",
            "job_target_id",
            "created_at",
            "id",
            postgresql_ops={"created_at": "DESC", "id": "DESC"},
        ),
        sa.Index(
            "ix_match_assessments_tuple_created",
            "jd_version_id",
            "resume_version_id",
            "policy_version",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        sa.Index(
            "uq_match_assessments_active_tuple",
            "jd_version_id",
            "resume_version_id",
            "policy_version",
            unique=True,
            postgresql_where=sa.text("status IN ('queued', 'evaluating')"),
        ),
        sa.Index(
            "ix_match_assessments_active_watchdog",
            "status",
            "updated_at",
            postgresql_where=sa.text("status IN ('queued', 'evaluating')"),
        ),
    )


def downgrade() -> None:
    op.drop_table("match_assessments")
