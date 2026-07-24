"""add llm config verified state (verified/last_verified_at)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 已有配置向后兼容：默认 verified=false，last_verified_at 为空
    op.add_column(
        'llm_configs',
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'llm_configs',
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('llm_configs', 'last_verified_at')
    op.drop_column('llm_configs', 'verified')
