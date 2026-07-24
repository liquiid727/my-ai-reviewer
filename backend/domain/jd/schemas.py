"""JD 匹配相关数据模型 —— 定义输入与匹配结果结构。"""


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
