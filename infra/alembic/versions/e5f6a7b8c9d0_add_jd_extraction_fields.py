"""add jd extraction fields

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 存量 JD 向后兼容：职责为空列表、来源标记为 manual
    op.add_column(
        'job_descriptions',
        sa.Column('responsibilities', JSONB(), nullable=False, server_default='[]'),
    )
    op.add_column(
        'job_descriptions',
        sa.Column('seniority', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'job_descriptions',
        sa.Column(
            'extraction_source',
            sa.String(length=20),
            nullable=False,
            server_default='manual',
        ),
    )


def downgrade() -> None:
    op.drop_column('job_descriptions', 'extraction_source')
    op.drop_column('job_descriptions', 'seniority')
    op.drop_column('job_descriptions', 'responsibilities')
