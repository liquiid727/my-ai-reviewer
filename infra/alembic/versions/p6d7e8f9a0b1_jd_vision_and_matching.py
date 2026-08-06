"""add JD vision import and hybrid matching contracts

Revision ID: p6d7e8f9a0b1
Revises: o5c6d7e8f9a0
Create Date: 2026-08-05
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p6d7e8f9a0b1"
down_revision: Union[str, None] = "o5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_configs",
        sa.Column(
            "capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("llm_configs", sa.Column("capabilities_verified_at", sa.DateTime(timezone=True), nullable=True))

    op.drop_constraint("ck_jd_source_type", "job_descriptions", type_="check")
    op.drop_constraint("ck_jd_processing_step", "job_descriptions", type_="check")
    op.add_column("job_descriptions", sa.Column("structured_revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column(
        "job_descriptions",
        sa.Column(
            "hard_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("job_descriptions", sa.Column("vision_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("job_descriptions", sa.Column("source_asset_count", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_jd_source_type", "job_descriptions", "source_type IN ('text', 'file', 'url', 'image')")
    op.create_check_constraint(
        "ck_jd_processing_step",
        "job_descriptions",
        "processing_step IN ('queued', 'source_validate', 'source_extract', 'vision_extract', 'text_quality_check', 'duplicate_check', 'llm_extract', 'done')",
    )

    op.create_table(
        "jd_source_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jd_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=50), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="stored"),
        sa.Column(
            "transcript_blocks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("processing_error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('stored', 'transcribing', 'ready', 'failed', 'deleted')", name="ck_jd_asset_status"),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jd_id", "order_index", name="uq_jd_source_asset_order"),
    )
    op.create_index("ix_jd_assets_jd_order", "jd_source_assets", ["jd_id", "order_index"])

    op.add_column("jd_match_results", sa.Column("status", sa.String(length=20), nullable=False, server_default="ready"))
    op.add_column("jd_match_results", sa.Column("mode", sa.String(length=20), nullable=False, server_default="rules_v1"))
    op.add_column("jd_match_results", sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("jd_match_results", sa.Column("input_fingerprint", sa.String(length=64), nullable=True))
    op.add_column("jd_match_results", sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "jd_match_results",
        sa.Column("hard_filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "jd_match_results",
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "jd_match_results",
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("jd_match_results", sa.Column("coverage", sa.Float(), nullable=True))
    op.add_column("jd_match_results", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("jd_match_results", sa.Column("matcher_version", sa.String(length=80), nullable=False, server_default="rules-v1"))
    op.add_column("jd_match_results", sa.Column("hard_filter_policy_version", sa.String(length=80), nullable=True))
    op.add_column("jd_match_results", sa.Column("prompt_version", sa.String(length=80), nullable=True))
    op.add_column("jd_match_results", sa.Column("schema_version", sa.String(length=80), nullable=True))
    op.add_column("jd_match_results", sa.Column("provider", sa.String(length=50), nullable=True))
    op.add_column("jd_match_results", sa.Column("model_name", sa.String(length=100), nullable=True))
    op.add_column("jd_match_results", sa.Column("failure_code", sa.String(length=80), nullable=True))
    op.add_column("jd_match_results", sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jd_match_results", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jd_match_results", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jd_match_results", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.alter_column("jd_match_results", "match_score", existing_type=sa.Float(), nullable=True)
    op.alter_column("jd_match_results", "recommendation", existing_type=sa.String(length=20), type_=sa.String(length=30), existing_nullable=False)
    op.create_check_constraint("ck_jd_match_status", "jd_match_results", "status IN ('queued', 'running', 'ready', 'failed', 'stale')")
    op.create_check_constraint("ck_jd_match_mode", "jd_match_results", "mode IN ('rules_v1', 'hybrid_v2')")
    op.create_index("ix_jd_match_results_fingerprint", "jd_match_results", ["jd_id", "resume_id", "mode", "input_fingerprint"])
    op.create_index(
        "uq_jd_match_ready_fingerprint",
        "jd_match_results",
        ["jd_id", "resume_id", "mode", "input_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'ready' AND input_fingerprint IS NOT NULL"),
    )
    op.create_index(
        "uq_jd_match_active_fingerprint",
        "jd_match_results",
        ["jd_id", "resume_id", "mode", "input_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running') AND input_fingerprint IS NOT NULL"),
    )

    op.add_column("job_search_plans", sa.Column("match_input_fingerprint", sa.String(length=64), nullable=True))
    op.add_column(
        "job_search_plans",
        sa.Column("match_stale_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.add_column("interviews", sa.Column("jd_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("interviews", sa.Column("match_result_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("interviews", sa.Column("jd_context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("interviews", sa.Column("match_context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("interviews", sa.Column("context_fingerprint", sa.String(length=64), nullable=True))
    op.create_foreign_key("fk_interviews_jd_id", "interviews", "job_descriptions", ["jd_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_interviews_match_result_id", "interviews", "jd_match_results", ["match_result_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_interviews_jd", "interviews", ["jd_id"])
    op.create_index("ix_interviews_match_result", "interviews", ["match_result_id"])


def downgrade() -> None:
    op.drop_index("ix_interviews_match_result", table_name="interviews")
    op.drop_index("ix_interviews_jd", table_name="interviews")
    op.drop_constraint("fk_interviews_match_result_id", "interviews", type_="foreignkey")
    op.drop_constraint("fk_interviews_jd_id", "interviews", type_="foreignkey")
    op.drop_column("interviews", "context_fingerprint")
    op.drop_column("interviews", "match_context_snapshot")
    op.drop_column("interviews", "jd_context_snapshot")
    op.drop_column("interviews", "match_result_id")
    op.drop_column("interviews", "jd_id")
    op.drop_column("job_search_plans", "match_stale_reasons")
    op.drop_column("job_search_plans", "match_input_fingerprint")
    op.drop_index("uq_jd_match_active_fingerprint", table_name="jd_match_results")
    op.drop_index("uq_jd_match_ready_fingerprint", table_name="jd_match_results")
    op.drop_index("ix_jd_match_results_fingerprint", table_name="jd_match_results")
    op.drop_constraint("ck_jd_match_mode", "jd_match_results", type_="check")
    op.drop_constraint("ck_jd_match_status", "jd_match_results", type_="check")
    for col in [
        "updated_at",
        "completed_at",
        "started_at",
        "attempt",
        "failure_code",
        "model_name",
        "provider",
        "schema_version",
        "prompt_version",
        "hard_filter_policy_version",
        "matcher_version",
        "confidence",
        "coverage",
        "evidence",
        "dimension_scores",
        "hard_filters",
        "input_snapshot",
        "input_fingerprint",
        "processing_run_id",
        "mode",
        "status",
    ]:
        op.drop_column("jd_match_results", col)
    op.alter_column("jd_match_results", "match_score", existing_type=sa.Float(), nullable=False)
    op.alter_column("jd_match_results", "recommendation", existing_type=sa.String(length=30), type_=sa.String(length=20), existing_nullable=False)
    op.drop_index("ix_jd_assets_jd_order", table_name="jd_source_assets")
    op.drop_table("jd_source_assets")
    op.drop_constraint("ck_jd_processing_step", "job_descriptions", type_="check")
    op.drop_constraint("ck_jd_source_type", "job_descriptions", type_="check")
    op.create_check_constraint("ck_jd_source_type", "job_descriptions", "source_type IN ('text', 'file', 'url')")
    op.create_check_constraint(
        "ck_jd_processing_step",
        "job_descriptions",
        "processing_step IN ('queued', 'source_extract', 'duplicate_check', 'llm_extract', 'done')",
    )
    op.drop_column("job_descriptions", "source_asset_count")
    op.drop_column("job_descriptions", "vision_metadata")
    op.drop_column("job_descriptions", "hard_requirements")
    op.drop_column("job_descriptions", "structured_revision")
    op.drop_column("llm_configs", "capabilities_verified_at")
    op.drop_column("llm_configs", "capabilities")
