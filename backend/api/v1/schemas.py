from datetime import datetime
from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


class ResumeUploadData(BaseModel):
    resume_id: str
    file_id: str
    status: str


class ResumeStatusData(BaseModel):
    status: str
    current_step: str
    completed_steps: list[str]
    error: str | None = None


class ResumeDetailData(BaseModel):
    resume_id: str
    status: str
    raw_text: str | None = None
    parsed_result: dict | None = None
    created_at: datetime
    updated_at: datetime


class EvaluationData(BaseModel):
    evaluation_id: str
    resume_id: str
    overall_score: float
    dimension_scores: dict
    strengths: list | dict
    risks: list | dict
    interview_suggestions: list | dict
    summary: str | None = None
    llm_model: str | None = None
    created_at: datetime
