"""add resume processing run ownership and safe diagnostics

Revision ID: n4b5c6d7e8f9
Revises: m3a4b5c6d7e8
Create Date: 2026-08-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "n4b5c6d7e8f9"
down_revision: Union[str, None] = "m3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resume_processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="queued", nullable=False),
        sa.Column("current_step", sa.String(length=40), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("attempt", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_progress_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name="fk_resume_processing_runs_resume_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_processing_runs_resume_created",
        "resume_processing_runs",
        ["resume_id", "created_at"],
    )
    op.create_index(
        "ix_resume_processing_runs_deadline",
        "resume_processing_runs",
        ["status", "deadline_at"],
    )
    op.create_index(
        "uq_resume_processing_runs_active",
        "resume_processing_runs",
        ["resume_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running', 'waiting_review')"),
    )
    op.add_column(
        "resumes",
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "resumes",
        sa.Column("processing_error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_resumes_processing_run_id",
        "resumes",
        "resume_processing_runs",
        ["processing_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Give pre-existing orphaned in-flight rows a durable owner.  They retain
    # their old timestamps so the watchdog/status endpoint can converge them
    # to a retryable failure instead of polling forever.
    op.execute(
        sa.text(
            """
            INSERT INTO resume_processing_runs
                (id, resume_id, run_type, status, current_step, last_progress_at, deadline_at)
            SELECT
                gen_random_uuid(),
                r.id,
                'legacy_recovery',
                CASE WHEN r.status = 'privacy_review_required' THEN 'waiting_review' ELSE 'running' END,
                CASE r.status
                    WHEN 'uploaded' THEN 'text_extract'
                    WHEN 'privacy_scanning' THEN 'text_extract'
                    WHEN 'privacy_review_required' THEN 'privacy_scan'
                    WHEN 'text_masked' THEN 'llm_parse'
                    WHEN 'llm_parsing' THEN 'llm_parse'
                    WHEN 'fact_extracted' THEN 'classify'
                    WHEN 'classified' THEN 'evaluate'
                    WHEN 'evaluating' THEN 'evaluate'
                END,
                COALESCE(r.updated_at, r.created_at, now()),
                CASE
                    WHEN r.status = 'privacy_review_required' THEN NULL
                    ELSE COALESCE(r.updated_at, r.created_at, now()) + interval '600 seconds'
                END
            FROM resumes r
            WHERE r.status IN (
                'uploaded', 'privacy_scanning', 'privacy_review_required', 'text_masked',
                'llm_parsing', 'fact_extracted', 'classified', 'evaluating'
            )
              AND NOT EXISTS (
                  SELECT 1 FROM resume_processing_runs existing
                  WHERE existing.resume_id = r.id
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE resumes r
            SET processing_run_id = run.id
            FROM resume_processing_runs run
            WHERE run.resume_id = r.id
              AND run.run_type = 'legacy_recovery'
              AND r.processing_run_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_resumes_processing_run_id", "resumes", type_="foreignkey")
    op.drop_column("resumes", "processing_error_details")
    op.drop_column("resumes", "processing_run_id")
    op.drop_index("uq_resume_processing_runs_active", table_name="resume_processing_runs")
    op.drop_index("ix_resume_processing_runs_deadline", table_name="resume_processing_runs")
    op.drop_index("ix_resume_processing_runs_resume_created", table_name="resume_processing_runs")
    op.drop_table("resume_processing_runs")
