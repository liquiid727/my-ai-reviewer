"""add interview tables

Revision ID: a1b2c3d4e5f6
Revises: 167205c7c871
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '167205c7c871'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'interviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('resumes.id'), nullable=False),
        sa.Column('jd_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('question_count', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('graph_thread_id', sa.String(100), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_interviews_resume', 'interviews', ['resume_id'])
    op.create_index('ix_interviews_status', 'interviews', ['status'])

    op.create_table(
        'interview_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence_num', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('stage', sa.String(30), nullable=False),
        sa.Column('difficulty', sa.String(20), nullable=False),
        sa.Column('expected_points', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('jd_relevance', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('interview_id', 'sequence_num', name='uq_interview_question_seq'),
    )

    op.create_table(
        'question_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('question_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('interview_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('is_followup', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('followup_round', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('followup_question', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('key_points_hit', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('key_points_missed', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('needs_followup', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('raw_llm_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_answers_question', 'question_answers', ['question_id'])

    op.create_table(
        'interview_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('dimension_scores', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('per_question_summary', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('strengths', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('weaknesses', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('recommendation', sa.String(20), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('interview_reports')
    op.drop_index('ix_answers_question', table_name='question_answers')
    op.drop_table('question_answers')
    op.drop_table('interview_questions')
    op.drop_index('ix_interviews_status', table_name='interviews')
    op.drop_index('ix_interviews_resume', table_name='interviews')
    op.drop_table('interviews')
