"""数据库 ORM 模型 —— 定义所有数据表的映射关系。"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
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


class InterviewModel(Base):
    """面试会话表 —— 存储面试会话的状态和配置。"""
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    graph_thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    resume: Mapped["ResumeModel"] = relationship(lazy="selectin")
    questions: Mapped[list["InterviewQuestionModel"]] = relationship(
        back_populates="interview", lazy="selectin", order_by="InterviewQuestionModel.sequence_num",
    )
    report: Mapped["InterviewReportModel | None"] = relationship(
        back_populates="interview", uselist=False, lazy="selectin",
    )

    __table_args__ = (
        Index("ix_interviews_resume", "resume_id"),
        Index("ix_interviews_status", "status"),
    )


class InterviewQuestionModel(Base):
    """面试题目表 —— 存储 LLM 生成的面试题目及预期答案要点。"""
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False,
    )
    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_points: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    jd_relevance: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["InterviewModel"] = relationship(back_populates="questions")
    answers: Mapped[list["QuestionAnswerModel"]] = relationship(
        back_populates="question", lazy="selectin", order_by="QuestionAnswerModel.followup_round",
    )

    __table_args__ = (
        UniqueConstraint("interview_id", "sequence_num", name="uq_interview_question_seq"),
    )


class QuestionAnswerModel(Base):
    """回答记录表 —— 存储候选人每轮回答的文本、评分和追问信息。"""
    __tablename__ = "question_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_followup: Mapped[bool] = mapped_column(default=False)
    followup_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    followup_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points_hit: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    key_points_missed: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    needs_followup: Mapped[bool] = mapped_column(default=False)
    raw_llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question: Mapped["InterviewQuestionModel"] = relationship(back_populates="answers")

    __table_args__ = (
        Index("ix_answers_question", "question_id"),
    )


class InterviewReportModel(Base):
    """面试报告表 —— 存储 LLM 生成的综合面试评估报告。"""
    __tablename__ = "interview_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    per_question_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    strengths: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    weaknesses: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["InterviewModel"] = relationship(back_populates="report")


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
