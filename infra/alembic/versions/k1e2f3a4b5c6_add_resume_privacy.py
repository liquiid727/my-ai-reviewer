"""add resume privacy manifests and masked data contracts

Revision ID: k1e2f3a4b5c6
Revises: j0e1f2a3b4c5
Create Date: 2026-08-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k1e2f3a4b5c6"
down_revision: Union[str, None] = "j0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("resumes", "raw_text", new_column_name="masked_text")
    op.add_column(
        "resume_drafts",
        sa.Column(
            "privacy_manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_table(
        "resume_privacy_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="legacy_pending"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("policy_version", sa.String(length=50), nullable=False, server_default="resume-privacy-v1"),
        sa.Column("engine_version", sa.String(length=50), nullable=False, server_default="local-redactor-v1"),
        sa.Column("placeholders", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("quarantine_path", sa.String(length=1000), nullable=True),
        sa.Column("quarantine_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id"),
    )
    op.create_index("ix_resume_privacy_status", "resume_privacy_manifests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_resume_privacy_status", table_name="resume_privacy_manifests")
    op.drop_table("resume_privacy_manifests")
    op.drop_column("resume_drafts", "privacy_manifest")
    op.alter_column("resumes", "masked_text", new_column_name="raw_text")
