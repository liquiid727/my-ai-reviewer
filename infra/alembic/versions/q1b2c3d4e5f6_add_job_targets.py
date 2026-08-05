"""add job_targets workspace

Revision ID: q1b2c3d4e5f6
Revises: p0a1b2c3d4e5
Create Date: 2026-08-05

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "q1b2c3d4e5f6"
down_revision: Union[str, None] = "p0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_description_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_jd_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("default_resume_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_description_id"], ["job_descriptions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["default_jd_version_id"], ["job_description_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["default_resume_version_id"], ["resume_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_targets_jd", "job_targets", ["job_description_id"])
    op.create_index("ix_job_targets_default_jd_version", "job_targets", ["default_jd_version_id"])
    op.create_index(
        "ix_job_targets_default_resume_version", "job_targets", ["default_resume_version_id"]
    )
    # One active (non-archived) target per JD identity in the anonymous scope.
    op.create_index(
        "uq_job_targets_active_jd",
        "job_targets",
        ["job_description_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_index("ix_job_targets_updated_id", "job_targets", ["updated_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_job_targets_updated_id", table_name="job_targets")
    op.drop_index("uq_job_targets_active_jd", table_name="job_targets")
    op.drop_index("ix_job_targets_default_resume_version", table_name="job_targets")
    op.drop_index("ix_job_targets_default_jd_version", table_name="job_targets")
    op.drop_index("ix_job_targets_jd", table_name="job_targets")
    op.drop_table("job_targets")
