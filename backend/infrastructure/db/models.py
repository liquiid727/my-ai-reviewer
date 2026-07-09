"""数据库 ORM 模型 —— 定义所有数据表的映射关系。"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.infrastructure.db.database import Base


class UserModel(Base):
    """用户表 —— 存储注册用户信息。"""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 用户关联的所有简历
    resumes: Mapped[list["ResumeModel"]] = relationship(back_populates="user", lazy="selectin")


class FileModel(Base):
    """文件表 —— 记录上传到对象存储的文件元信息。"""
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)    # 原始文件名
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)    # MinIO 存储路径
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)     # MIME 类型
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)           # 文件大小（字节）
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # 文件哈希（去重用）
    owner_type: Mapped[str] = mapped_column(String(50), nullable=False)        # 所有者类型（如 "resume"）
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_files_owner", "owner_type", "owner_id"),  # 按所有者查询的联合索引
    )


class ResumeModel(Base):
    """简历表 —— 存储简历的处理状态、原始文本和解析结果。"""
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    file_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")  # 处理状态
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)           # 提取的原始文本
    parsed_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)    # LLM 解析结果（JSON）
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 解析器版本
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)        # 失败时的错误信息
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    user: Mapped["UserModel | None"] = relationship(back_populates="resumes", lazy="selectin")
    evaluations: Mapped[list["ResumeEvaluationModel"]] = relationship(
        back_populates="resume", lazy="selectin", order_by="ResumeEvaluationModel.created_at",
    )


class ResumeEvaluationModel(Base):
    """简历评估表 —— 存储 LLM 对简历的评估结果。"""
    __tablename__ = "resume_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)                # 综合评分
    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # 各维度评分
    strengths: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)         # 优势列表
    risks: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)             # 风险列表
    interview_suggestions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)  # 面试建议
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)                    # 总结评语
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)           # 使用的模型名称
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resume: Mapped["ResumeModel"] = relationship(back_populates="evaluations", lazy="selectin")


class LLMConfigModel(Base):
    """LLM 配置表 —— 存储各 LLM 提供商的连接配置。"""
    __tablename__ = "llm_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)          # 提供商（openai/anthropic/deepseek）
    api_key_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)  # 加密后的 API Key
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)       # 模型名称
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)   # 自定义 API 地址
    is_active: Mapped[bool] = mapped_column(default=True)                      # 是否启用
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
