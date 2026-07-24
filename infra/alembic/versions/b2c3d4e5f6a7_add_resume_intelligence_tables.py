"""add resume intelligence tables (sections/facts/profiles/jd/match)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'resume_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('section_index', sa.Integer(), nullable=False),
        sa.Column('section_type', sa.String(50), nullable=True),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_resume_sections_resume', 'resume_sections', ['resume_id'])

    op.create_table(
        'resume_facts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fact_type', sa.String(50), nullable=False),
        sa.Column('fact_key', sa.String(200), nullable=False),
        sa.Column('fact_value', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('evidence_source_text', sa.Text(), nullable=True),
        sa.Column('evidence_page', sa.Integer(), nullable=True),
        sa.Column('evidence_section', sa.String(100), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('parser_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_resume_facts_resume', 'resume_facts', ['resume_id'])
    op.create_index('ix_resume_facts_type', 'resume_facts', ['resume_id', 'fact_type'])

    op.create_table(
        'candidate_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('resumes.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('identity', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('education', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('work_experiences', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('projects', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('skills', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('certificates', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('ability_tags', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('interview_clues', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('risks', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('parser_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_candidate_profiles_resume', 'candidate_profiles', ['resume_id'])

    op.create_table(
        'job_descriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('company', sa.String(200), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('required_skills', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('structured', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'jd_match_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jd_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('job_descriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_score', sa.Float(), nullable=False),
        sa.Column('skill_match', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('missing_skills', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('risk', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('gap', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('recommendation', sa.String(20), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_jd_match_results_resume', 'jd_match_results', ['resume_id'])
    op.create_index('ix_jd_match_results_jd', 'jd_match_results', ['jd_id'])


def downgrade() -> None:
    op.drop_index('ix_jd_match_results_jd', table_name='jd_match_results')
    op.drop_index('ix_jd_match_results_resume', table_name='jd_match_results')
    op.drop_table('jd_match_results')
    op.drop_table('job_descriptions')
    op.drop_index('ix_candidate_profiles_resume', table_name='candidate_profiles')
    op.drop_table('candidate_profiles')
    op.drop_index('ix_resume_facts_type', table_name='resume_facts')
    op.drop_index('ix_resume_facts_resume', table_name='resume_facts')
    op.drop_table('resume_facts')
    op.drop_index('ix_resume_sections_resume', table_name='resume_sections')
    op.drop_table('resume_sections')
