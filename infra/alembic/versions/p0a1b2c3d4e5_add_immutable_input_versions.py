"""add immutable JD/Resume input versions

Revision ID: p0a1b2c3d4e5
Revises: o5c6d7e8f9a0
Create Date: 2026-08-05

"""
from collections.abc import Sequence
from typing import Union

import hashlib
import json
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p0a1b2c3d4e5"
down_revision: Union[str, None] = "o5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. JD immutable version snapshot (RIP-010 10.1).
    op.create_table(
        "job_description_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_description_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("structured", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("publication_reason", sa.String(length=100), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_description_id"], ["job_descriptions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_description_id", "version_no"),
        sa.UniqueConstraint("job_description_id", "content_hash", "schema_version"),
    )
    op.create_index(
        "ix_jd_versions_jd", "job_description_versions", ["job_description_id"]
    )

    # 2. Resume immutable version snapshot (RIP-010 10.2).
    op.create_table(
        "resume_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("masked_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("profile_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("evidence_catalog", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("privacy_policy_version", sa.String(length=50), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["draft_id"], ["resume_drafts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "source_type IN ('parsed_resume', 'builder_draft')",
            name="ck_resume_versions_source_type",
        ),
        sa.CheckConstraint(
            "(source_type = 'parsed_resume' AND resume_id IS NOT NULL AND draft_id IS NULL) OR "
            "(source_type = 'builder_draft' AND draft_id IS NOT NULL)",
            name="ck_resume_versions_single_source",
        ),
    )
    op.create_index("ix_resume_versions_resume", "resume_versions", ["resume_id"])
    op.create_index("ix_resume_versions_draft", "resume_versions", ["draft_id"])
    # One content snapshot per parsed resume; one per builder revision/content hash.
    op.create_index(
        "uq_resume_versions_parsed_content",
        "resume_versions",
        ["resume_id", "content_hash"],
        unique=True,
        postgresql_where=sa.text("resume_id IS NOT NULL"),
    )
    op.create_index(
        "uq_resume_versions_draft_content",
        "resume_versions",
        ["draft_id", "source_revision", "content_hash"],
        unique=True,
        postgresql_where=sa.text("draft_id IS NOT NULL"),
    )

    # 3. Link current JD version after the version table exists.
    op.add_column(
        "job_descriptions",
        sa.Column(
            "current_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_job_descriptions_current_version",
        "job_descriptions",
        "job_description_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 4. Backfill every ready JD as version 1. Missing metadata is represented
    #    as legacy/unavailable, never fabricated.
    connection = op.get_bind()
    ready_jds = connection.execute(
        sa.text(
            "SELECT id, raw_text, structured, content_hash, parser_version, "
            "       title, company, location, required_skills, responsibilities, "
            "       preferred_skills, seniority, field_sources, source_type, "
            "       source_url, source_file_id, created_at "
            "FROM job_descriptions WHERE status = 'ready'"
        )
    ).fetchall()

    for row in ready_jds:
        (
            jd_id, raw_text, structured, existing_hash, parser_version,
            title, company, location, required_skills, responsibilities,
            preferred_skills, seniority, field_sources, source_type,
            source_url, source_file_id, created_at,
        ) = row

        normalized = (raw_text or "").strip()
        structured_snapshot = dict(structured or {})
        structured_snapshot.setdefault("title", title)
        structured_snapshot.setdefault("company", company)
        structured_snapshot.setdefault("location", location)
        structured_snapshot.setdefault("required_skills", required_skills or [])
        structured_snapshot.setdefault("responsibilities", responsibilities or [])
        structured_snapshot.setdefault("preferred_skills", preferred_skills or [])
        structured_snapshot.setdefault("seniority", seniority)

        # Evidence is only what already exists in field_sources; nothing fabricated.
        evidence = {"field_sources": field_sources} if field_sources else {}
        source_metadata = {
            "source_type": source_type or "text",
            "source_url": source_url,
            "source_file_id": str(source_file_id) if source_file_id else None,
        }
        version_hash = existing_hash or hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        version_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO job_description_versions "
                "(id, job_description_id, version_no, normalized_text, structured, evidence, "
                " source_metadata, content_hash, parser_version, model_name, schema_version, "
                " publication_reason, published_at) "
                "VALUES (:id, :jd_id, 1, :normalized, CAST(:structured AS jsonb), CAST(:evidence AS jsonb), "
                "CAST(:source_meta AS jsonb), :content_hash, :parser_version, NULL, :schema_version, "
                "'legacy_backfill', :published_at)"
            ),
            {
                "id": version_id,
                "jd_id": jd_id,
                "normalized": normalized,
                "structured": json.dumps(structured_snapshot, ensure_ascii=False),
                "evidence": json.dumps(evidence, ensure_ascii=False),
                "source_meta": json.dumps(source_metadata, ensure_ascii=False),
                "content_hash": version_hash,
                "parser_version": parser_version or "legacy",
                "schema_version": "jd-v1",
                "published_at": created_at,
            },
        )
        connection.execute(
            sa.text("UPDATE job_descriptions SET current_version_id = :vid WHERE id = :jd_id"),
            {"vid": version_id, "jd_id": jd_id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_job_descriptions_current_version", "job_descriptions", type_="foreignkey")
    op.drop_column("job_descriptions", "current_version_id")
    op.drop_index("uq_resume_versions_draft_content", table_name="resume_versions")
    op.drop_index("uq_resume_versions_parsed_content", table_name="resume_versions")
    op.drop_index("ix_resume_versions_draft", table_name="resume_versions")
    op.drop_index("ix_resume_versions_resume", table_name="resume_versions")
    op.drop_table("resume_versions")
    op.drop_index("ix_jd_versions_jd", table_name="job_description_versions")
    op.drop_table("job_description_versions")
