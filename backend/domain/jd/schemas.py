"""JD 匹配相关数据模型 —— 定义输入、匹配结果与 LLM 抽取结果结构。"""


from typing import Literal

from pydantic import BaseModel, Field


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
    name: str
    critical: bool = False       # 是否关键技能
    evidence: str | None = None  # 支撑该技能要求的 JD 原文片段


class JDExtraction(BaseModel):
    """LLM JD 抽取结果（RIP-003 v1.1）。

    required_skills / responsibilities 必填：键缺失或键名走样的 LLM 输出
    会触发 ValidationError 走重试→报错链路，避免静默返回空结果。
    """
    required_skills: list[ExtractedSkill]
    responsibilities: list[str]
    seniority: Literal["junior", "mid", "senior", "expert"] = "mid"

    @property
    def skill_names(self) -> list[str]:
        """全部技能名，供落库/匹配复用。"""
        return [s.name for s in self.required_skills]

    @property
    def critical_skills(self) -> list[str]:
        """关键技能名子集。"""
        return [s.name for s in self.required_skills if s.critical]

