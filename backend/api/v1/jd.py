"""JD 匹配相关 API 端点 —— 创建 JD、触发匹配、查询匹配结果。"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import (
    APIResponse,
    JDMatchRequest,
    JDMatchResultData,
    JobDescriptionData,
)
from backend.domain.jd.matching import JDMatchingService
from backend.domain.jd.schemas import JobDescriptionInput
from backend.infrastructure.db.database import get_db
from backend.infrastructure.db.models import (
    JDMatchResultModel,
    JobDescriptionModel,
    ResumeModel,
)

router = APIRouter(prefix="/jd", tags=["jd"])


@router.post("", response_model=APIResponse)
async def create_job_description(
    payload: JobDescriptionInput,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """创建职位描述（JD），返回其 id。"""
    required_skills = [
        {"name": name, "critical": name in (payload.critical_skills or [])}
        for name in payload.required_skills
    ]
    jd = JobDescriptionModel(
        title=payload.title,
        company=payload.company,
        raw_text=payload.raw_text,
        required_skills=required_skills,
    )
    session.add(jd)
    await session.flush()

    data = JobDescriptionData(
        id=str(jd.id),
        title=jd.title,
        company=jd.company,
        raw_text=jd.raw_text,
        required_skills=jd.required_skills,
        created_at=jd.created_at,
    )
    await session.commit()
    return APIResponse(data=data.model_dump(mode="json"))


@router.get("/{jd_id}", response_model=APIResponse)
async def get_job_description(
    jd_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取 JD 详情。"""
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=404, message="Job description not found")

    data = JobDescriptionData(
        id=str(jd.id),
        title=jd.title,
        company=jd.company,
        raw_text=jd.raw_text,
        required_skills=jd.required_skills,
        created_at=jd.created_at,
    )
    return APIResponse(data=data.model_dump(mode="json"))


@router.post("/match", response_model=APIResponse)
async def match_resume_to_jd(
    payload: JDMatchRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """对简历与 JD 执行匹配。

    若提供 jd_id 则使用已有 JD；否则用请求中的 jd 字段现场创建 JD 后匹配。
    """
    resume_id = uuid.UUID(payload.resume_id)
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    if payload.jd_id:
        jd = await session.get(JobDescriptionModel, uuid.UUID(payload.jd_id))
        if jd is None:
            return APIResponse(code=404, message="Job description not found")
    elif payload.jd:
        required_skills = [
            {"name": name, "critical": name in (payload.jd.critical_skills or [])}
            for name in payload.jd.required_skills
        ]
        jd = JobDescriptionModel(
            title=payload.jd.title,
            company=payload.jd.company,
            raw_text=payload.jd.raw_text,
            required_skills=required_skills,
        )
        session.add(jd)
        await session.flush()
    else:
        return APIResponse(code=400, message="Either jd_id or jd must be provided")

    service = JDMatchingService()
    record = await service.match(session, resume_id, jd)
    await session.commit()

    data = _match_row_to_dict(record)
    return APIResponse(data=data)


@router.get("/resume/{resume_id}/matches", response_model=APIResponse)
async def list_jd_matches(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """列出某简历的全部 JD 匹配结果（按时间倒序）。"""
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    stmt = select(JDMatchResultModel).where(JDMatchResultModel.resume_id == resume_id)
    result = await session.execute(stmt)
    records = result.scalars().all()

    data = [_match_row_to_dict(r) for r in records]
    return APIResponse(data=data)


@router.get("/match/{match_id}", response_model=APIResponse)
async def get_jd_match(
    match_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取单条 JD 匹配结果。"""
    record = await session.get(JDMatchResultModel, match_id)
    if record is None:
        return APIResponse(code=404, message="JD match result not found")

    return APIResponse(data=_match_row_to_dict(record))


def _match_row_to_dict(row: JDMatchResultModel) -> dict[str, Any]:
    """将 ORM 匹配结果行转为 API 响应字典。"""
    return JDMatchResultData(
        id=str(row.id),
        resume_id=str(row.resume_id),
        jd_id=str(row.jd_id),
        match_score=row.match_score,
        skill_match=row.skill_match,
        missing_skills=row.missing_skills,
        risk=row.risk,
        gap=row.gap,
        recommendation=row.recommendation,
        detail=row.detail,
        created_at=row.created_at,
    ).model_dump(mode="json")
