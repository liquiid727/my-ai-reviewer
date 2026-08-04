"""add persistent ordering for resume drafts

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resume_drafts",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    # 为已有草稿回填当前的更新时间倒序，避免升级后卡片顺序突然变化。
    op.execute(sa.text("""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       ORDER BY updated_at DESC NULLS LAST,
                                created_at DESC NULLS LAST,
                                id
                   ) - 1 AS position
            FROM resume_drafts
        )
        UPDATE resume_drafts AS drafts
        SET sort_order = ranked.position
        FROM ranked
        WHERE drafts.id = ranked.id
    """))
    op.alter_column("resume_drafts", "sort_order", server_default=None)


def downgrade() -> None:
    op.drop_column("resume_drafts", "sort_order")
