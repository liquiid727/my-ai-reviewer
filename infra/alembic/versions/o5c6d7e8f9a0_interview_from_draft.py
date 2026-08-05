"""allow creating interviews from builder drafts

Revision ID: o5c6d7e8f9a0
Revises: n4b5c6d7e8f9
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "o5c6d7e8f9a0"
down_revision: Union[str, None] = "n4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 支持从简历草稿（含未关联上传简历的独立草稿）发起面试：
    # resume_id 变为可空，草稿面试改用 resume_snapshot 保存出题用的脱敏内容快照。
    op.alter_column("interviews", "resume_id", existing_type=sa.UUID(), nullable=True)
    op.add_column(
        "interviews",
        sa.Column("resume_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interviews", "resume_snapshot")
    op.alter_column("interviews", "resume_id", existing_type=sa.UUID(), nullable=False)
