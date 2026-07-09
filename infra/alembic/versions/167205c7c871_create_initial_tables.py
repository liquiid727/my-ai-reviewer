"""创建初始数据库表

Revision ID: 167205c7c871
Revises:
Create Date: 2026-07-08 19:46:49.339954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Alembic 版本标识
revision: str = '167205c7c871'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：创建所有初始表。"""
    # 文件表 —— 存储上传文件的元信息
    op.create_table('files',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('original_name', sa.String(length=500), nullable=False),
    sa.Column('storage_path', sa.String(length=1000), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256_hash', sa.String(length=64), nullable=False),
    sa.Column('owner_type', sa.String(length=50), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_files_owner', 'files', ['owner_type', 'owner_id'], unique=False)
    op.create_index(op.f('ix_files_sha256_hash'), 'files', ['sha256_hash'], unique=False)

    # LLM 配置表 —— 存储各 LLM 提供商的配置
    op.create_table('llm_configs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('provider', sa.String(length=50), nullable=False),
    sa.Column('api_key_encrypted', sa.String(length=500), nullable=False),
    sa.Column('model_name', sa.String(length=100), nullable=False),
    sa.Column('base_url', sa.String(length=500), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    # 用户表
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )

    # 简历表 —— 存储简历的处理状态和解析结果
    op.create_table('resumes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('file_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=True),
    sa.Column('parsed_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('parser_version', sa.String(length=50), nullable=True),
    sa.Column('parse_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # 简历评估表 —— 存储 LLM 评估结果
    op.create_table('resume_evaluations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('resume_id', sa.UUID(), nullable=False),
    sa.Column('overall_score', sa.Float(), nullable=False),
    sa.Column('dimension_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('strengths', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('risks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('interview_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('llm_model', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """回退：按依赖顺序删除所有表。"""
    op.drop_table('resume_evaluations')
    op.drop_table('resumes')
    op.drop_table('users')
    op.drop_table('llm_configs')
    op.drop_index(op.f('ix_files_sha256_hash'), table_name='files')
    op.drop_index('ix_files_owner', table_name='files')
    op.drop_table('files')
