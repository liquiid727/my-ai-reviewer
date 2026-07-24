"""简历相关 API 端点 —— 上传、查询状态、查看详情、重试和获取评估结果。"""

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import (
    APIResponse,
    CandidateProfileData,
    EvaluationData,
    ResumeDetailData,
    ResumeFactData,
    ResumeStatusData,
    ResumeUploadData,
)
from backend.application.resume_service import upload_resume
from backend.domain.resume.enums import ResumeStatus
from backend.domain.resume.services import snapshot_and_reset_for_reparse
from backend.infrastructure.db.database import get_db
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    ResumeFactModel,
    ResumeModel,
)
from backend.tasks.resume_tasks import process_resume_pipeline

router = APIRouter(prefix="/resume", tags=["resume"])

# 处理流水线的四个步骤（按顺序执行）
PIPELINE_STEPS = ["text_extract", "llm_parse", "classify", "evaluate"]

# 状态 → 已完成到第几步的映射（-1 表示还没开始）
STATUS_TO_STEP_INDEX: dict[str, int] = {
    ResumeStatus.UPLOADED.value: -1,
    ResumeStatus.TEXT_PARSED.value: 0,
    ResumeStatus.FACT_EXTRACTED.value: 1,
    ResumeStatus.CLASSIFIED.value: 2,
    ResumeStatus.EVALUATED.value: 3,
}


def _completed_steps(status: str) -> list[str]:
    """根据状态值推算已完成的步骤列表。"""
    idx = STATUS_TO_STEP_INDEX.get(status, -1)
    return PIPELINE_STEPS[: idx + 1]


def _completed_steps_from_data(resume: ResumeModel) -> list[str]:
    """失败状态下，根据实际数据判断已完成的步骤（比单纯看状态更准确）。"""
    steps: list[str] = []
    if resume.raw_text:
        steps.append("text_extract")
    if resume.parsed_result:
        steps.append("llm_parse")
        if "classification" in (resume.parsed_result or {}):
            steps.append("classify")
    if resume.evaluations:
        steps.append("evaluate")
    return steps


def _current_step(status: str) -> str:
    """推算当前正在执行（或下一步将执行）的步骤名。"""
    if status == ResumeStatus.FAILED.value:
        return "failed"
    idx = STATUS_TO_STEP_INDEX.get(status, -1)
    if idx + 1 < len(PIPELINE_STEPS):
        return PIPELINE_STEPS[idx + 1]
    return "done"


@router.post("/upload", response_model=APIResponse)
async def upload_resume_endpoint(
    file: UploadFile,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """上传简历文件，自动触发处理流水线。"""
    file_data = await file.read()
    result = await upload_resume(
        session=session,
        filename=file.filename or "unknown",
        file_data=file_data,
    )
    return APIResponse(data=ResumeUploadData(**result))


@router.get("/{resume_id}/status", response_model=APIResponse)
async def get_resume_status(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """查询简历的处理状态和进度。"""
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    status = resume.status
    # 失败状态下从实际数据推断已完成步骤，避免状态不一致
    if status == ResumeStatus.FAILED.value:
        completed = _completed_steps_from_data(resume)
    else:
        completed = _completed_steps(status)
    data = ResumeStatusData(
        status=status,
        current_step=_current_step(status),
        completed_steps=completed,
        error=resume.parse_error,
    )
    return APIResponse(data=data.model_dump())


@router.get("/{resume_id}", response_model=APIResponse)
async def get_resume_detail(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历详情（含原始文本和 LLM 解析结果）。"""
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    data = ResumeDetailData(
        resume_id=str(resume.id),
        status=resume.status,
        raw_text=resume.raw_text,
        parsed_result=resume.parsed_result,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )
    return APIResponse(data=data.model_dump(mode="json"))


@router.get("/{resume_id}/facts", response_model=APIResponse)
async def get_resume_facts(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历抽取出的全部可追溯事实。"""
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    stmt = select(ResumeFactModel).where(ResumeFactModel.resume_id == resume_id)
    result = await session.execute(stmt)
    facts = result.scalars().all()

    data = [ResumeFactData(**_fact_row_to_dict(f)).model_dump(mode="json") for f in facts]
    return APIResponse(data=data)


@router.get("/{resume_id}/profile", response_model=APIResponse)
async def get_candidate_profile(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历对应的候选人画像（独立落库，便于检索与审计）。"""
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    stmt = select(CandidateProfileModel).where(CandidateProfileModel.resume_id == resume_id)
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        return APIResponse(code=404, message="No candidate profile found for this resume")

    data = CandidateProfileData(**_profile_row_to_dict(profile)).model_dump(mode="json")
    return APIResponse(data=data)


def _fact_row_to_dict(row: ResumeFactModel) -> dict[str, Any]:
    """将 ORM 事实行转为 Pydantic 模型可接受的字段字典。"""
    return {
        "id": str(row.id),
        "fact_type": row.fact_type,
        "fact_key": row.fact_key,
        "fact_value": row.fact_value,
        "evidence_source_text": row.evidence_source_text,
        "evidence_page": row.evidence_page,
        "evidence_section": row.evidence_section,
        "confidence": row.confidence,
        "metadata": row.meta,
        "parser_version": row.parser_version,
        "created_at": row.created_at,
    }


def _profile_row_to_dict(row: CandidateProfileModel) -> dict[str, Any]:
    """将 ORM 画像行转为 Pydantic 模型可接受的字段字典。"""
    return {
        "id": str(row.id),
        "resume_id": str(row.resume_id),
        "identity": row.identity,
        "education": row.education,
        "work_experiences": row.work_experiences,
        "projects": row.projects,
        "skills": row.skills,
        "certificates": row.certificates,
        "ability_tags": row.ability_tags,
        "interview_clues": row.interview_clues,
        "risks": row.risks,
        "parser_version": row.parser_version,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.post("/{resume_id}/retry", response_model=APIResponse)
async def retry_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """重试失败的简历处理流水线。"""
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    if resume.status != ResumeStatus.FAILED.value:
        return APIResponse(code=400, message="Resume is not in failed state")

    # 重置状态，清除错误信息
    resume.parse_error = None
    resume.status = ResumeStatus.UPLOADED.value
    await session.commit()

    # 重新派发处理流水线任务到 Celery
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_resume_pipeline, str(resume.id))
    except Exception:
        resume.status = ResumeStatus.FAILED.value
        resume.parse_error = "Failed to dispatch pipeline to broker"
        await session.commit()
        return APIResponse(code=503, message="Pipeline dispatch failed, please retry later")

    return APIResponse(
        message="Pipeline restarted",
        data=ResumeStatusData(
            status=ResumeStatus.UPLOADED.value,
            current_step="text_extract",
            completed_steps=[],
        ).model_dump(),
    )


@router.post("/{resume_id}/reparse", response_model=APIResponse)
async def reparse_resume_endpoint(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """对任意已存简历重新解析（从 text_extract 起重跑），并保留上一版本快照。

    与 /retry 不同：/retry 仅适用于 failed 状态；/reparse 适用于任意状态（如
    parser/extractor 版本升级后对历史简历重跑），并将当前结果快照入历史。
    """
    try:
        resume = await snapshot_and_reset_for_reparse(session, resume_id)
    except ValueError:
        return APIResponse(code=404, message="Resume not found")

    # 重新派发处理流水线任务到 Celery
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_resume_pipeline, str(resume.id))
    except Exception:
        resume.status = ResumeStatus.FAILED.value
        resume.parse_error = "Failed to dispatch pipeline to broker"
        await session.commit()
        return APIResponse(code=503, message="Pipeline dispatch failed, please retry later")

    return APIResponse(
        message="Re-parse started",
        data=ResumeStatusData(
            status=ResumeStatus.UPLOADED.value,
            current_step="text_extract",
            completed_steps=[],
        ).model_dump(),
    )


@router.get("/{resume_id}/evaluation", response_model=APIResponse)
async def get_evaluation(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历的 LLM 评估结果（取最新一次评估）。"""
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    if not resume.evaluations:
        return APIResponse(code=404, message="No evaluation found for this resume")

    # 取最新一条评估记录
    eval_record = resume.evaluations[-1]
    data = EvaluationData(
        evaluation_id=str(eval_record.id),
        resume_id=str(eval_record.resume_id),
        overall_score=eval_record.overall_score,
        dimension_scores=eval_record.dimension_scores,
        strengths=eval_record.strengths,
        risks=eval_record.risks,
        interview_suggestions=eval_record.interview_suggestions,
        summary=eval_record.summary,
        llm_model=eval_record.llm_model,
        created_at=eval_record.created_at,
    )
    return APIResponse(data=data.model_dump(mode="json"))
