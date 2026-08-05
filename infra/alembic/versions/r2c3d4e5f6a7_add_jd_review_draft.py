"""add JD review draft columns

Revision ID: r2c3d4e5f6a7
Revises: q1b2c3d4e5f6
Create Date: 2026-08-05

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "r2c3d4e5f6a7"
down_revision: Union[str, None] = "q1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_descriptions",
        sa.Column("review_revision", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("review_draft", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("review_error", sa.Text(), nullable=True),
    )
    op.drop_constraint("ck_jd_status", "job_descriptions", type_="check")
    op.create_check_constraint(
        "ck_jd_status",
        "job_descriptions",
        "status IN ('processing', 'duplicate_pending', 'needs_review', 'ready', 'failed', 'archived')",
    )
    op.drop_constraint("ck_jd_processing_step", "job_descriptions", type_="check")
    op.create_check_constraint(
        "ck_jd_processing_step",
        "job_descriptions",
        "processing_step IN ('queued', 'source_extract', 'duplicate_check', 'structure_parse', "
        "'llm_extract', 'review', 'done')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_jd_processing_step", "job_descriptions", type_="check")
    op.create_check_constraint(
        "ck_jd_processing_step",
        "job_descriptions",
        "processing_step IN ('queued', 'source_extract', 'duplicate_check', 'llm_extract', 'done')",
    )
    op.drop_constraint("ck_jd_status", "job_descriptions", type_="check")
    op.create_check_constraint(
        "ck_jd_status",
        "job_descriptions",
        "status IN ('processing', 'duplicate_pending', 'ready', 'failed')",
    )
    op.drop_column("job_descriptions", "review_error")
    op.drop_column("job_descriptions", "review_draft")
    op.drop_column("job_descriptions", "review_revision")
