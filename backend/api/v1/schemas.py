"""API 响应数据模型 —— 定义接口统一返回格式和各业务数据结构。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.domain.jd.schemas import JobDescriptionInput


class APIResponse(BaseModel):
    """统一 API 响应格式：code=0 表示成功，非零表示错误。"""

    code: int = 0
    message: str = "success"
    data: Any = None


class ResumeUploadData(BaseModel):
    """简历上传成功后的返回数据。"""

    resume_id: str
    status: str
    run_id: str | None = None
    error_code: str | None = None


class ResumeFailureDiagnostic(BaseModel):
    """Safe failure fields used to correlate a failed processing run."""

    error_code: str
    step: str | None = None
    attempt: int | None = None
    retryable: bool = False


class ResumeStatusData(BaseModel):
    """简历处理流水线的状态信息。"""

    status: str  # 当前总状态
    current_step: str  # 正在执行的步骤
    completed_steps: list[str]  # 已完成的步骤列表
    error: str | None = None  # 失败时的错误信息
    run_id: str | None = None
    error_code: str | None = None
    retryable: bool = False
    last_progress_at: datetime | None = None
    deadline_at: datetime | None = None
    diagnostic: ResumeFailureDiagnostic | None = None


class ResumeDetailData(BaseModel):
    """Resume detail containing approved masked text and parsed results."""

    resume_id: str
    status: str
    masked_text: str | None = None
    parsed_result: dict[str, Any] | None = None
    privacy: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class EvaluationData(BaseModel):
    """简历评估结果数据。"""

    evaluation_id: str
    resume_id: str
    overall_score: float  # 综合评分 (0-100)
    dimension_scores: dict[str, Any]  # 各维度评分
    strengths: list[Any] | dict[str, Any]  # 优势
    risks: list[Any] | dict[str, Any]  # 风险点
    interview_suggestions: list[Any] | dict[str, Any]  # 面试建议
    summary: str | None = None  # 总结
    llm_model: str | None = None  # 使用的 LLM 模型
    created_at: datetime


class ResumeFactData(BaseModel):
    """单条可追溯事实的数据。"""

    id: str
    fact_type: str
    fact_key: str
    fact_value: dict[str, Any] | None = None
    evidence_source_text: str | None = None
    evidence_page: int | None = None
    evidence_section: str | None = None
    confidence: float
    metadata: dict[str, Any] | None = None
    parser_version: str | None = None
    created_at: datetime


class CandidateProfileData(BaseModel):
    """候选人画像数据。"""

    id: str
    resume_id: str
    identity: dict[str, Any] | None = None
    education: list[Any] | dict[str, Any] | None = None
    work_experiences: list[Any] | dict[str, Any] | None = None
    projects: list[Any] | dict[str, Any] | None = None
    skills: list[Any] | dict[str, Any] | None = None
    certificates: list[Any] | dict[str, Any] | None = None
    ability_tags: list[Any] | dict[str, Any] | None = None
    interview_clues: list[Any] | dict[str, Any] | None = None
    risks: list[Any] | dict[str, Any] | None = None
    parser_version: str | None = None
    created_at: datetime
    updated_at: datetime


class JobDescriptionData(BaseModel):
    """职位描述数据。"""

    id: str
    title: str | None = None
    company: str | None = None
    raw_text: str
    required_skills: list[Any] | dict[str, Any] | None = None
    responsibilities: list[Any] | None = None  # 岗位职责（LLM 抽取）
    seniority: str | None = None  # junior/mid/senior/expert
    extraction_source: str | None = None  # manual | llm
    source_type: str | None = None
    source_url: str | None = None
    source_file_id: str | None = None
    source_assets: list[Any] | None = None
    source_asset_count: int | None = None
    vision: dict[str, Any] | None = None
    processing_run_id: str | None = None
    location: str | None = None
    preferred_skills: list[Any] | dict[str, Any] | None = None
    status: str | None = None
    processing_step: str | None = None
    processing_error: str | None = None
    duplicate_of_id: str | None = None
    field_sources: dict[str, Any] | None = None
    parser_version: str | None = None
    structured_revision: int | None = None
    hard_requirements: list[Any] | None = None
    updated_at: datetime | None = None
    created_at: datetime


class JDMatchRequest(BaseModel):
    """触发 JD 匹配的请求。"""

    resume_id: str
    jd_id: str | None = None  # 已存在的 JD；或传 jd 现场创建
    jd: JobDescriptionInput | None = None  # 现场创建 JD（jd_id 为空时必填）


class JDMatchResultData(BaseModel):
    """JD 匹配结果数据。"""

    id: str
    resume_id: str
    jd_id: str
    match_score: float | None = None
    skill_match: list[Any] | dict[str, Any] | None = None
    missing_skills: list[Any] | dict[str, Any] | None = None
    risk: list[Any] | dict[str, Any] | None = None
    gap: list[Any] | dict[str, Any] | None = None
    recommendation: str
    detail: str | None = None
    status: str | None = None
    mode: str | None = None
    input_fingerprint: str | None = None
    hard_filters: list[Any] | None = None
    dimension_scores: list[Any] | None = None
    evidence: list[Any] | None = None
    coverage: float | None = None
    confidence: float | None = None
    human_confirmation_required: bool | None = None
    matcher_version: str | None = None
    hard_filter_policy_version: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None
    model: dict[str, Any] | None = None
    stale: bool | None = None
    stale_reasons: list[str] | None = None
    failure_code: str | None = None
    updated_at: datetime | None = None
    created_at: datetime
