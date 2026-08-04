"""add resume AI assistant proposals and draft revisions

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h8c9d0e1f2a3"
down_revision: Union[str, None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resume_drafts",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "resume_edit_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("llm_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["draft_id"], ["resume_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["llm_config_id"], ["llm_configs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resume_edit_sessions_draft", "resume_edit_sessions", ["draft_id"])

    op.create_table(
        "resume_edit_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["resume_edit_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_resume_edit_message_sequence"),
    )
    op.create_index("ix_resume_edit_messages_session", "resume_edit_messages", ["session_id"])

    op.create_table(
        "resume_edit_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_request_id", sa.String(100), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("assistant_message", sa.Text(), nullable=False),
        sa.Column("operations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selected_operation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="proposed"),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("before_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("applied_revision", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["resume_edit_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_request_id"),
    )
    op.create_index("ix_resume_edit_proposals_session", "resume_edit_proposals", ["session_id"])
    op.create_index("ix_resume_edit_proposals_status", "resume_edit_proposals", ["status"])


def downgrade() -> None:
    op.drop_index("ix_resume_edit_proposals_status", table_name="resume_edit_proposals")
    op.drop_index("ix_resume_edit_proposals_session", table_name="resume_edit_proposals")
    op.drop_table("resume_edit_proposals")
    op.drop_index("ix_resume_edit_messages_session", table_name="resume_edit_messages")
    op.drop_table("resume_edit_messages")
    op.drop_index("ix_resume_edit_sessions_draft", table_name="resume_edit_sessions")
    op.drop_table("resume_edit_sessions")
    op.drop_column("resume_drafts", "revision")
