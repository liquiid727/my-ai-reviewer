"""persist latest AI score on resume drafts

Revision ID: m3a4b5c6d7e8
Revises: l2f3a4b5c6d7
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "m3a4b5c6d7e8"
down_revision: Union[str, None] = "l2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 草稿级 AI 评分持久化：保存最近一次完整评分结果、评分时间与评分时的草稿版本。
    # scored_revision 与当前 revision 不一致即表示「简历已更新，可重新评分」。
    op.add_column(
        "resume_drafts",
        sa.Column("latest_score", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "resume_drafts",
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "resume_drafts",
        sa.Column("scored_revision", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_drafts", "scored_revision")
    op.drop_column("resume_drafts", "scored_at")
    op.drop_column("resume_drafts", "latest_score")
