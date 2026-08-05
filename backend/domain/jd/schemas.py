"""JD library and matching contracts."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl

from backend.domain.jd.enums import JDProcessingStep, JDSourceType, JDStatus


class RequiredSkill(BaseModel):
    """岗位必备技能。"""

    name: str
    critical: bool = False  # 是否关键技能（缺失将显著影响结论）


class SkillMatchItem(BaseModel):
    """单项技能匹配结果。"""

    skill: str
    matched: bool
    critical: bool = False
    candidate_evidence: str | None = None  # 候选人在简历中体现该技能的证据


class RiskItem(BaseModel):
    """风险点。"""

    level: str  # high | medium | low
    message: str


class GapItem(BaseModel):
    """差距分析项。"""

    area: str
    description: str


class JDMatchResult(BaseModel):
    """JD 匹配结论。"""

    match_score: float = Field(ge=0, le=100)
    skill_match: list[SkillMatchItem] = []
    missing_skills: list[str] = []
    risk: list[RiskItem] = []
    gap: list[GapItem] = []
    recommendation: str  # strong_hire | hire | conditional | reject
    detail: str | None = None


class JobDescriptionInput(BaseModel):
    """创建 JD 的输入。"""

    title: str | None = None
    company: str | None = None
    raw_text: str
    required_skills: list[str] = []
    critical_skills: list[str] = []


class ExtractedSkill(BaseModel):
    """LLM 从 JD 原文抽取的单项技能，附原文证据便于追溯。"""

    name: str = Field(min_length=1, max_length=500)
    critical: bool = False  # 是否关键技能
    evidence: str | None = Field(default=None, max_length=500)  # 支撑该技能要求的 JD 原文片段


JDResponsibility = Annotated[str, Field(min_length=1, max_length=500)]


class JDExtraction(BaseModel):
    """LLM JD 抽取结果（RIP-003 v1.1）。

    required_skills / responsibilities 必填：键缺失或键名走样的 LLM 输出
    会触发 ValidationError 走重试→报错链路，避免静默返回空结果。
    """

    title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    required_skills: list[ExtractedSkill] = Field(max_length=100)
    preferred_skills: list[ExtractedSkill] = Field(default_factory=list, max_length=100)
    responsibilities: list[JDResponsibility] = Field(max_length=50)
    seniority: Literal["junior", "mid", "senior", "expert"] | None = None

    @property
    def skill_names(self) -> list[str]:
        """全部技能名，供落库/匹配复用。"""
        return [s.name for s in self.required_skills]

    @property
    def critical_skills(self) -> list[str]:
        """关键技能名子集。"""
        return [s.name for s in self.required_skills if s.critical]


class DraftItem(BaseModel):
    """A structured draft list item with stable key, evidence, and provenance."""

    key: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=500)
    evidence: str | None = Field(default=None, max_length=500)
    evidence_status: Literal["available", "unavailable"] = "unavailable"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: Literal["source", "llm", "manual"] = "llm"


class HardConditionItem(BaseModel):
    """A hard requirement (years/education/language/certificate/location)."""

    key: str = Field(min_length=1, max_length=200)
    category: Literal["years", "education", "language", "certificate", "location", "other"]
    value: str = Field(min_length=1, max_length=500)
    evidence: str | None = Field(default=None, max_length=500)
    evidence_status: Literal["available", "unavailable"] = "unavailable"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: Literal["source", "llm", "manual"] = "llm"


class CompensationRange(BaseModel):
    min_amount: int | None = Field(default=None, ge=0)
    max_amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    period: Literal["yearly", "monthly", "hourly"] | None = None


class ReviewDraft(BaseModel):
    """Complete structured JD review draft (RIP-011 §6.1).

    Scalar uncertainty is null; list uncertainty is []. Every list item and
    hard requirement carries a stable key, optional evidence, confidence, and
    provenance. Missing evidence is `unavailable`, never a fabricated quote.
    """

    title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    employment_type: Literal["full_time", "part_time", "contract", "internship"] | None = None
    seniority: Literal["junior", "mid", "senior", "expert"] | None = None
    compensation: CompensationRange | None = None

    minimum_years: int | None = Field(default=None, ge=0, le=50)
    preferred_years: int | None = Field(default=None, ge=0, le=50)
    education: str | None = Field(default=None, max_length=200)
    languages: list[str] = Field(default_factory=list, max_length=20)
    certificates: list[str] = Field(default_factory=list, max_length=50)
    location_constraint: str | None = Field(default=None, max_length=200)

    responsibilities: list[DraftItem] = Field(default_factory=list, max_length=50)
    required_skills: list[DraftItem] = Field(default_factory=list, max_length=100)
    preferred_skills: list[DraftItem] = Field(default_factory=list, max_length=100)
    hard_conditions: list[HardConditionItem] = Field(default_factory=list, max_length=100)
    domain_context: str | None = Field(default=None, max_length=500)
    industry_context: str | None = Field(default=None, max_length=500)
    interview_clues: list[str] = Field(default_factory=list, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)

    parser_version: str | None = Field(default=None, max_length=50)
    model_name: str | None = Field(default=None, max_length=200)
    prompt_version: str | None = Field(default=None, max_length=50)
    schema_version: str = Field(default="jd-review-v1", max_length=50)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class JDExtractionResult(BaseModel):
    """Extractor output envelope: parsed draft plus metadata, never raw provider text."""

    draft: ReviewDraft
    parser_version: str
    model_name: str | None = None
    prompt_version: str | None = None
    schema_version: str = "jd-review-v1"


class JDReviewPatchRequest(BaseModel):
    """Revision-safe structured review edit request."""

    expected_review_revision: int = Field(ge=0)
    draft: ReviewDraft


class JDTextImportRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=100_000)
    title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    allow_duplicate: bool = False


class JDURLImportRequest(BaseModel):
    url: HttpUrl
    allow_duplicate: bool = False


class JDStructuredPatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    seniority: Literal["junior", "mid", "senior", "expert"] | None = None
    responsibilities: list[JDResponsibility] | None = Field(default=None, max_length=50)
    required_skills: list[ExtractedSkill] | None = Field(default=None, max_length=100)
    preferred_skills: list[ExtractedSkill] | None = Field(default=None, max_length=100)
    expected_updated_at: datetime


class JDReextractRequest(BaseModel):
    overwrite_manual: bool = False


class JDSummary(BaseModel):
    id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    source_type: JDSourceType
    status: JDStatus
    processing_step: JDProcessingStep
    updated_at: datetime
