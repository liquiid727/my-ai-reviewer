"""面试领域数据模型 —— 定义面试问答流程中各环节的 Pydantic 模型。"""

from pydantic import BaseModel, Field


class InterviewQuestion(BaseModel):
    """LLM 生成的单道面试题。"""

    question_text: str
    stage: str
    difficulty: str
    expected_points: list[str] = Field(default_factory=list)
    jd_relevance: str | None = None


class QuestionGenerationOutput(BaseModel):
    """LLM 出题的完整输出。"""

    questions: list[InterviewQuestion]


class AnswerEvaluation(BaseModel):
    """LLM 对候选人回答的评估结果。"""

    score: float = Field(ge=0, le=100)
    feedback: str
    key_points_hit: list[str] = Field(default_factory=list)
    key_points_missed: list[str] = Field(default_factory=list)
    needs_followup: bool = False
    followup_reason: str | None = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class FollowupOutput(BaseModel):
    """LLM 生成的追问题目。"""

    followup_question: str


class DimensionScore(BaseModel):
    """报告中单个维度的评分。"""

    name: str
    score: float = Field(ge=0, le=100)
    reason: str


class QuestionSummary(BaseModel):
    """报告中单题的总结。"""

    question_num: int
    question_text: str
    final_score: float
    summary: str


class StrengthWeakness(BaseModel):
    """报告中的优势/劣势条目。"""

    point: str
    evidence: str


class InterviewReport(BaseModel):
    """LLM 生成的面试报告完整输出。"""

    overall_score: float = Field(ge=0, le=100)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    per_question_summary: list[QuestionSummary] = Field(default_factory=list)
    strengths: list[StrengthWeakness] = Field(default_factory=list)
    weaknesses: list[StrengthWeakness] = Field(default_factory=list)
    recommendation: str
    summary: str | None = None
