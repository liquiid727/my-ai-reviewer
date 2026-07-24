"""add resume builder tables (drafts/exports)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'resume_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(200), nullable=False, server_default='我的简历'),
        sa.Column('content', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('template_id', sa.String(50), nullable=False, server_default='classic'),
        sa.Column('design_tokens', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('auto_one_page', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_resume_drafts_resume', 'resume_drafts', ['resume_id'])

    op.create_table(
        'resume_exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('draft_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('resume_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('storage_path', sa.String(1000), nullable=False),
        sa.Column('template_id', sa.String(50), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_resume_exports_draft', 'resume_exports', ['draft_id'])


def downgrade() -> None:
    op.drop_index('ix_resume_exports_draft', table_name='resume_exports')
    op.drop_table('resume_exports')
    op.drop_index('ix_resume_drafts_resume', table_name='resume_drafts')
    op.drop_table('resume_drafts')
