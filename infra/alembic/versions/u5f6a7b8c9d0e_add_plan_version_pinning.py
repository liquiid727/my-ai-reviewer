"""Add version-pinned references to job_search_plans (RIP-014 #112).

Revision ID: u5f6a7b8c9d0e
Revises: t4e5f6a7b8c9
Create Date: 2026-08-05

Add nullable, indexed, RESTRICT foreign keys pinning a plan to the Job
Target, immutable JD/Resume Versions, and a completed Match Assessment,
plus a partial uniqueness rule over the version tuple for unfinished
plans. Legacy rows keep null references and the legacy uniqueness rule;
the migration never guesses historical version references.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "u5f6a7b8c9d0e"
down_revision: Union[str, None] = "t4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_search_plans",
        sa.Column(
            "job_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_targets.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "job_search_plans",
        sa.Column(
            "jd_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_description_versions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "job_search_plans",
        sa.Column(
            "resume_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resume_versions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "job_search_plans",
        sa.Column(
            "match_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("match_assessments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_plans_job_target", "job_search_plans", ["job_target_id"])
    op.create_index("ix_plans_jd_version", "job_search_plans", ["jd_version_id"])
    op.create_index("ix_plans_resume_version", "job_search_plans", ["resume_version_id"])
    op.create_index("ix_plans_match_assessment", "job_search_plans", ["match_assessment_id"])
    # Version-pinned unfinished plans are unique over the full tuple; equality
    # fields precede the status predicate, matching RIP-008 unfinished statuses.
    op.create_index(
        "uq_versioned_plan_tuple",
        "job_search_plans",
        ["job_target_id", "jd_version_id", "resume_version_id", "match_assessment_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('generating', 'regenerating', 'active', 'failed')"),
    )


def downgrade() -> None:
    op.drop_index("uq_versioned_plan_tuple", table_name="job_search_plans")
    op.drop_index("ix_plans_match_assessment", table_name="job_search_plans")
    op.drop_index("ix_plans_resume_version", table_name="job_search_plans")
    op.drop_index("ix_plans_jd_version", table_name="job_search_plans")
    op.drop_index("ix_plans_job_target", table_name="job_search_plans")
    op.drop_column("job_search_plans", "match_assessment_id")
    op.drop_column("job_search_plans", "resume_version_id")
    op.drop_column("job_search_plans", "jd_version_id")
    op.drop_column("job_search_plans", "job_target_id")
