"""API 响应数据模型 —— 定义接口统一返回格式和各业务数据结构。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    """统一 API 响应格式：code=0 表示成功，非零表示错误。"""
    code: int = 0
    message: str = "success"
    data: Any = None


class ResumeUploadData(BaseModel):
    """简历上传成功后的返回数据。"""
    resume_id: str
    file_id: str
    status: str


class ResumeStatusData(BaseModel):
    """简历处理流水线的状态信息。"""
    status: str            # 当前总状态
    current_step: str      # 正在执行的步骤
    completed_steps: list[str]  # 已完成的步骤列表
    error: str | None = None    # 失败时的错误信息


class ResumeDetailData(BaseModel):
    """简历详情（含原始文本和解析结果）。"""
    resume_id: str
    status: str
    raw_text: str | None = None
    parsed_result: dict | None = None
    created_at: datetime
    updated_at: datetime


class EvaluationData(BaseModel):
    """简历评估结果数据。"""
    evaluation_id: str
    resume_id: str
    overall_score: float           # 综合评分 (0-100)
    dimension_scores: dict         # 各维度评分
    strengths: list | dict         # 优势
    risks: list | dict             # 风险点
    interview_suggestions: list | dict  # 面试建议
    summary: str | None = None     # 总结
    llm_model: str | None = None   # 使用的 LLM 模型
    created_at: datetime
