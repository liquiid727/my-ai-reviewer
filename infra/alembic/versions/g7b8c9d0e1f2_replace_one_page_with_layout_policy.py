"""replace one-page flag with pagination policy

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resume_drafts",
        sa.Column("layout_mode", sa.String(50), nullable=False, server_default="auto_pages"),
    )
    op.add_column("resume_drafts", sa.Column("target_page_count", sa.Integer(), nullable=True))
    op.drop_column("resume_drafts", "auto_one_page")

    op.add_column(
        "resume_exports",
        sa.Column("layout_mode", sa.String(50), nullable=False, server_default="auto_pages"),
    )
    op.add_column("resume_exports", sa.Column("target_page_count", sa.Integer(), nullable=True))
    op.add_column(
        "resume_exports",
        sa.Column("applied_density", sa.String(50), nullable=False, server_default="normal"),
    )
    op.add_column(
        "resume_exports",
        sa.Column("target_met", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.add_column(
        "resume_drafts",
        sa.Column("auto_one_page", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_column("resume_exports", "target_met")
    op.drop_column("resume_exports", "applied_density")
    op.drop_column("resume_exports", "target_page_count")
    op.drop_column("resume_exports", "layout_mode")
    op.drop_column("resume_drafts", "target_page_count")
    op.drop_column("resume_drafts", "layout_mode")
