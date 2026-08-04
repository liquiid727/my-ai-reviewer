"""align resume fact metadata column with the ORM contract

Revision ID: l2f3a4b5c6d7
Revises: k1e2f3a4b5c6
Create Date: 2026-08-04
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "l2f3a4b5c6d7"
down_revision: Union[str, None] = "k1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("resume_facts", "metadata", new_column_name="meta")


def downgrade() -> None:
    op.alter_column("resume_facts", "meta", new_column_name="metadata")
