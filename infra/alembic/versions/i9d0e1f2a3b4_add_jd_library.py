"""add JD library lifecycle and provenance fields

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i9d0e1f2a3b4"
down_revision: Union[str, None] = "h8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("job_descriptions", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "job_descriptions",
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="text"),
    )
    op.add_column("job_descriptions", sa.Column("source_url", sa.String(length=2048), nullable=True))
    op.add_column("job_descriptions", sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("job_descriptions", sa.Column("location", sa.String(length=200), nullable=True))
    op.add_column(
        "job_descriptions",
        sa.Column(
            "preferred_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ready"),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("processing_step", sa.String(length=30), nullable=False, server_default="done"),
    )
    op.add_column("job_descriptions", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("job_descriptions", sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("job_descriptions", sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("job_descriptions", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "job_descriptions",
        sa.Column(
            "field_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("job_descriptions", sa.Column("parser_version", sa.String(length=50), nullable=True))
    op.add_column(
        "job_descriptions",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_foreign_key("fk_jd_user", "job_descriptions", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "fk_jd_source_file", "job_descriptions", "files", ["source_file_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_jd_duplicate_of", "job_descriptions", "job_descriptions", ["duplicate_of_id"], ["id"], ondelete="SET NULL"
    )
    op.create_check_constraint(
        "ck_jd_source_type", "job_descriptions", "source_type IN ('text', 'file', 'url')"
    )
    op.create_check_constraint(
        "ck_jd_status", "job_descriptions", "status IN ('processing', 'duplicate_pending', 'ready', 'failed')"
    )
    op.create_check_constraint(
        "ck_jd_processing_step",
        "job_descriptions",
        "processing_step IN ('queued', 'source_extract', 'duplicate_check', 'llm_extract', 'done')",
    )

    op.execute(
        """
        UPDATE job_descriptions
        SET source_type = 'text',
            status = 'ready',
            processing_step = 'done',
            updated_at = created_at,
            field_sources = jsonb_build_object(
                'required_skills', COALESCE(extraction_source, 'manual'),
                'responsibilities', COALESCE(extraction_source, 'manual'),
                'seniority', COALESCE(extraction_source, 'manual')
            )
        """
    )
    op.create_index("ix_jd_user_updated", "job_descriptions", ["user_id", "updated_at"])
    op.create_index("ix_jd_user_status", "job_descriptions", ["user_id", "status"])
    op.create_index("ix_jd_user_source", "job_descriptions", ["user_id", "source_type"])
    op.create_index("ix_jd_user_content_hash", "job_descriptions", ["user_id", "content_hash"])


def downgrade() -> None:
    op.drop_index("ix_jd_user_content_hash", table_name="job_descriptions")
    op.drop_index("ix_jd_user_source", table_name="job_descriptions")
    op.drop_index("ix_jd_user_status", table_name="job_descriptions")
    op.drop_index("ix_jd_user_updated", table_name="job_descriptions")
    op.drop_constraint("ck_jd_processing_step", "job_descriptions", type_="check")
    op.drop_constraint("ck_jd_status", "job_descriptions", type_="check")
    op.drop_constraint("ck_jd_source_type", "job_descriptions", type_="check")
    op.drop_constraint("fk_jd_duplicate_of", "job_descriptions", type_="foreignkey")
    op.drop_constraint("fk_jd_source_file", "job_descriptions", type_="foreignkey")
    op.drop_constraint("fk_jd_user", "job_descriptions", type_="foreignkey")
    op.drop_column("job_descriptions", "updated_at")
    op.drop_column("job_descriptions", "parser_version")
    op.drop_column("job_descriptions", "field_sources")
    op.drop_column("job_descriptions", "content_hash")
    op.drop_column("job_descriptions", "duplicate_of_id")
    op.drop_column("job_descriptions", "processing_run_id")
    op.drop_column("job_descriptions", "processing_error")
    op.drop_column("job_descriptions", "processing_step")
    op.drop_column("job_descriptions", "status")
    op.drop_column("job_descriptions", "preferred_skills")
    op.drop_column("job_descriptions", "location")
    op.drop_column("job_descriptions", "source_file_id")
    op.drop_column("job_descriptions", "source_url")
    op.drop_column("job_descriptions", "source_type")
    op.drop_column("job_descriptions", "user_id")
