"""数据库 ORM 模型 —— 定义所有数据表的映射关系。"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

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
    parsed_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)    # LLM 解析结果（JSON）
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 解析器版本
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)        # 失败时的错误信息
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关联关系
    user: Mapped["UserModel | None"] = relationship(back_populates="resumes", lazy="selectin")
    evaluations: Mapped[list["ResumeEvaluationModel"]] = relationship(
        back_populates="resume", lazy="selectin", order_by="ResumeEvaluationModel.created_at",
    )
    # 简历智能层：可追溯的结构化数据
    candidate_profile: Mapped["CandidateProfileModel | None"] = relationship(
        back_populates="resume", lazy="selectin", uselist=False, cascade="all, delete-orphan",
    )
    facts: Mapped[list["ResumeFactModel"]] = relationship(
        back_populates="resume", lazy="selectin", cascade="all, delete-orphan",
        order_by="ResumeFactModel.created_at",
    )
    sections: Mapped[list["ResumeSectionModel"]] = relationship(
        back_populates="resume", lazy="selectin", cascade="all, delete-orphan",
        order_by="ResumeSectionModel.section_index",
    )
    jd_matches: Mapped[list["JDMatchResultModel"]] = relationship(
        back_populates="resume", lazy="selectin", order_by="JDMatchResultModel.created_at",
    )


class ResumeEvaluationModel(Base):
    """简历评估表 —— 存储 LLM 对简历的评估结果。"""
    __tablename__ = "resume_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)                # 综合评分
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # 各维度评分
    strengths: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)         # 优势列表
    risks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)             # 风险列表
    interview_suggestions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)  # 面试建议
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
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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
    expected_points: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
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
    key_points_hit: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    key_points_missed: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    needs_followup: Mapped[bool] = mapped_column(default=False)
    raw_llm_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
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
    dimension_scores: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    per_question_summary: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    strengths: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    weaknesses: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
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
    verified: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False,
    )  # 是否通过连通性测试（简历上传硬门禁的判定依据）
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )  # 最近一次测试通过的时间（verified 不设过期）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResumeSectionModel(Base):
    """简历区块表 —— 存储解析出的语义区块（工作经历/教育/技能等），用于事实溯源。"""
    __tablename__ = "resume_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False,
    )
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)        # 区块在文档中的顺序
    section_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 区块类型（work/education/skills/...）
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)      # 区块标题
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)               # 区块原文
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)           # 所在页码（PDF 有值）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resume: Mapped["ResumeModel"] = relationship(back_populates="sections", lazy="selectin")

    __table_args__ = (
        Index("ix_resume_sections_resume", "resume_id"),
    )


class ResumeFactModel(Base):
    """简历事实表 —— 从简历中抽取的单条结构化事实，带原文证据与置信度，实现可追溯。"""
    __tablename__ = "resume_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False,
    )
    fact_type: Mapped[str] = mapped_column(String(50), nullable=False)         # 事实类型（见 FactType 枚举）
    fact_key: Mapped[str] = mapped_column(String(200), nullable=False)         # 标识键（公司名/学校名/技能名）
    fact_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # 结构化值
    evidence_source_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # 原文证据摘录
    evidence_page: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 证据所在页码
    evidence_section: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 证据所在区块
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 置信度 (0~1)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # 附加元数据
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 抽取器版本
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resume: Mapped["ResumeModel"] = relationship(back_populates="facts", lazy="selectin")

    __table_args__ = (
        Index("ix_resume_facts_resume", "resume_id"),
        Index("ix_resume_facts_type", "resume_id", "fact_type"),
    )


class CandidateProfileModel(Base):
    """候选人画像表 —— 聚合一份简历的全部结构化信息，独立于简历主表便于检索与审计。"""
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    identity: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)       # 身份信息
    education: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)      # 教育背景
    work_experiences: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)  # 工作经历
    projects: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)       # 项目经历
    skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)         # 技能清单
    certificates: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)   # 证书
    ability_tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)   # 能力标签（分类器生成）
    interview_clues: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)  # 面试线索
    risks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)          # 风险点
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)     # 抽取器版本
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    resume: Mapped["ResumeModel"] = relationship(back_populates="candidate_profile", lazy="selectin")

    __table_args__ = (
        Index("ix_candidate_profiles_resume", "resume_id"),
    )


class ResumeDraftModel(Base):
    """简历草稿表 —— 可编辑的结构化简历，为「简历制作」提供编辑/渲染/导出的数据源。"""
    __tablename__ = "resume_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 可空：允许脱离已解析简历的独立草稿（为「从零新建」预留）
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="我的简历")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # 结构化草稿
    template_id: Mapped[str] = mapped_column(String(50), nullable=False, default="classic")  # 模板
    design_tokens: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # 设计令牌
    layout_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="auto_pages")
    target_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    # 列表级排序位置；越小越靠前，由草稿列表的上移/下移操作维护。
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    exports: Mapped[list["ResumeExportModel"]] = relationship(
        back_populates="draft", lazy="selectin", cascade="all, delete-orphan",
        order_by="ResumeExportModel.created_at",
    )

    __table_args__ = (
        Index("ix_resume_drafts_resume", "resume_id"),
    )


class ResumeEditSessionModel(Base):
    """一份草稿的 AI 编辑对话。"""
    __tablename__ = "resume_edit_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_drafts.id", ondelete="CASCADE"), nullable=False,
    )
    llm_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_configs.id", ondelete="SET NULL"), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (Index("ix_resume_edit_sessions_draft", "draft_id"),)


class ResumeEditMessageModel(Base):
    """AI 编辑会话中的有序消息。"""
    __tablename__ = "resume_edit_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_edit_sessions.id", ondelete="CASCADE"), nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_resume_edit_message_sequence"),
        Index("ix_resume_edit_messages_session", "session_id"),
    )


class ResumeEditProposalModel(Base):
    """可审阅、可原子应用和撤销的结构化修改提案。"""
    __tablename__ = "resume_edit_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_edit_sessions.id", ondelete="CASCADE"), nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    base_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    assistant_message: Mapped[str] = mapped_column(Text, nullable=False)
    operations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    selected_operation_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="proposed")
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    before_content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    applied_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_resume_edit_proposals_session", "session_id"),
        Index("ix_resume_edit_proposals_status", "status"),
    )


class ResumeExportModel(Base):
    """简历导出记录表 —— 记录每次导出的 PDF 对象与元信息，可追溯。"""
    __tablename__ = "resume_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_drafts.id", ondelete="CASCADE"), nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)   # MinIO 对象名
    template_id: Mapped[str] = mapped_column(String(50), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    layout_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    target_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applied_density: Mapped[str] = mapped_column(String(50), nullable=False)
    target_met: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    draft: Mapped["ResumeDraftModel"] = relationship(back_populates="exports", lazy="selectin")

    __table_args__ = (
        Index("ix_resume_exports_draft", "draft_id"),
    )


class JobDescriptionModel(Base):
    """职位描述表 —— 存储 JD 原文与解析出的必备技能清单。"""
    __tablename__ = "job_descriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)       # 职位名称
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)     # 公司名称
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")     # JD 原文
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"), nullable=True,
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    required_skills: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list,
    )  # 必备技能 [{name, critical, evidence?}]
    responsibilities: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list,
    )  # 岗位职责（LLM 抽取）
    preferred_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    seniority: Mapped[str | None] = mapped_column(String(20), nullable=True)  # junior/mid/senior/expert
    extraction_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual",
    )  # 技能清单来源：manual | llm
    structured: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)        # 结构化 JD（可选，LLM 解析）
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ready")
    processing_step: Mapped[str] = mapped_column(String(30), nullable=False, default="done")
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True,
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    field_sources: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("source_type IN ('text', 'file', 'url')", name="ck_jd_source_type"),
        CheckConstraint(
            "status IN ('processing', 'duplicate_pending', 'ready', 'failed')", name="ck_jd_status"
        ),
        CheckConstraint(
            "processing_step IN ('queued', 'source_extract', 'duplicate_check', 'llm_extract', 'done')",
            name="ck_jd_processing_step",
        ),
        Index("ix_jd_user_updated", "user_id", "updated_at"),
        Index("ix_jd_user_status", "user_id", "status"),
        Index("ix_jd_user_source", "user_id", "source_type"),
        Index("ix_jd_user_content_hash", "user_id", "content_hash"),
    )


class JDMatchResultModel(Base):
    """JD 匹配结果表 —— 存储候选人与岗位的匹配结论。"""
    __tablename__ = "jd_match_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False,
    )
    jd_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False,
    )
    match_score: Mapped[float] = mapped_column(Float, nullable=False)           # 综合匹配分 (0~100)
    skill_match: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)   # 逐项技能匹配
    missing_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)  # 缺失技能
    risk: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)     # 风险点
    gap: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)      # 差距分析
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)     # 推荐结论
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)            # 文字总结
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resume: Mapped["ResumeModel"] = relationship(back_populates="jd_matches", lazy="selectin")
    jd: Mapped["JobDescriptionModel"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_jd_match_results_resume", "resume_id"),
        Index("ix_jd_match_results_jd", "jd_id"),
    )


class JobSearchPlanModel(Base):
    """A durable, generated preparation plan for one ready JD and resume."""

    __tablename__ = "job_search_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    jd_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="RESTRICT"), nullable=False,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="RESTRICT"), nullable=False,
    )
    match_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jd_match_results.id", ondelete="SET NULL"), nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="generating")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weekly_hours: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    supplemental_background: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    tasks: Mapped[list["JobSearchPlanTaskModel"]] = relationship(
        back_populates="plan",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="JobSearchPlanTaskModel.sort_order",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('generating', 'regenerating', 'active', 'completed', 'failed')", name="ck_plan_status"
        ),
        CheckConstraint("weekly_hours IS NULL OR weekly_hours BETWEEN 1 AND 80", name="ck_plan_weekly_hours"),
        Index("ix_plans_user_updated", "user_id", "updated_at"),
        Index("ix_plans_user_status", "user_id", "status"),
        Index(
            "uq_active_plan_jd_resume",
            "jd_id",
            "resume_id",
            unique=True,
            postgresql_where=text("status IN ('generating', 'regenerating', 'active', 'failed')"),
        ),
    )


class JobSearchPlanTaskModel(Base):
    """One generated or manual task belonging to a job-search plan."""

    __tablename__ = "job_search_plan_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_search_plans.id", ondelete="CASCADE"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    basis: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="todo")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    plan: Mapped[JobSearchPlanModel] = relationship(back_populates="tasks", lazy="noload")

    __table_args__ = (
        CheckConstraint(
            "category IN ('gap_priority', 'resume', 'skill', 'evidence_project', 'interview', 'application_review')",
            name="ck_plan_task_category",
        ),
        CheckConstraint("source IN ('ai', 'manual')", name="ck_plan_task_source"),
        CheckConstraint("priority IN ('high', 'medium', 'low')", name="ck_plan_task_priority"),
        CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="ck_plan_task_status"),
        Index("ix_plan_tasks_plan_order", "plan_id", "sort_order"),
        Index("ix_plan_tasks_plan_status", "plan_id", "status"),
        Index("ix_plan_tasks_due_date", "due_date"),
    )
