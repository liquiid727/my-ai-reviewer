"""add image and manual JD source types

Revision ID: s3d4e5f6a7b8
Revises: r2c3d4e5f6a7
Create Date: 2026-08-05

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "s3d4e5f6a7b8"
down_revision: Union[str, None] = "r2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_jd_source_type", "job_descriptions", type_="check")
    op.create_check_constraint(
        "ck_jd_source_type",
        "job_descriptions",
        "source_type IN ('text', 'file', 'url', 'image', 'manual')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_jd_source_type", "job_descriptions", type_="check")
    op.create_check_constraint(
        "ck_jd_source_type",
        "job_descriptions",
        "source_type IN ('text', 'file', 'url')",
    )
