"""JD read-side use cases (list/get/match serialization helpers)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models import JDMatchResultModel, JobDescriptionModel, ResumeModel


async def get_jd(session: AsyncSession, jd_id: uuid.UUID) -> JobDescriptionModel | None:
    return await session.get(JobDescriptionModel, jd_id)


async def get_resume(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel | None:
    return await session.get(ResumeModel, resume_id)


async def get_match(session: AsyncSession, match_id: uuid.UUID) -> JDMatchResultModel | None:
    return await session.get(JDMatchResultModel, match_id)


def serialize_jd(jd: JobDescriptionModel, *, include_raw_text: bool = True) -> dict[str, Any]:
    return {
        "id": str(jd.id),
        "title": jd.title,
        "company": jd.company,
        "raw_text": jd.raw_text if include_raw_text else "",
        "required_skills": jd.required_skills,
        "responsibilities": jd.responsibilities,
        "seniority": jd.seniority,
        "extraction_source": jd.extraction_source,
        "source_type": jd.source_type,
        "source_url": jd.source_url,
        "source_file_id": str(jd.source_file_id) if jd.source_file_id else None,
        "location": jd.location,
        "preferred_skills": jd.preferred_skills,
        "status": jd.status,
        "processing_step": jd.processing_step,
        "processing_error": jd.processing_error,
        "duplicate_of_id": str(jd.duplicate_of_id) if jd.duplicate_of_id else None,
        "field_sources": jd.field_sources,
        "parser_version": jd.parser_version,
        "review_revision": jd.review_revision,
        "review_draft": jd.review_draft,
        "review_error": jd.review_error,
        "current_version_id": str(jd.current_version_id) if jd.current_version_id else None,
        "updated_at": jd.updated_at,
        "created_at": jd.created_at,
    }


def serialize_match(row: JDMatchResultModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "resume_id": str(row.resume_id),
        "jd_id": str(row.jd_id),
        "match_score": row.match_score,
        "skill_match": row.skill_match,
        "missing_skills": row.missing_skills,
        "risk": row.risk,
        "gap": row.gap,
        "recommendation": row.recommendation,
        "detail": row.detail,
        "created_at": row.created_at,
    }


async def list_matches_for_resume(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> list[dict[str, Any]] | None:
    resume = await get_resume(session, resume_id)
    if resume is None:
        return None
    result = await session.execute(
        select(JDMatchResultModel)
        .where(JDMatchResultModel.resume_id == resume_id)
        .order_by(JDMatchResultModel.created_at.desc())
    )
    return [serialize_match(row) for row in result.scalars().all()]


async def list_job_descriptions(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    q: str | None,
    source_type: Literal["text", "file", "url"] | None,
    status: Literal["processing", "duplicate_pending", "needs_review", "ready", "failed", "archived"] | None,
    direction: Literal["asc", "desc"],
) -> dict[str, Any]:
    conditions: list[Any] = []
    if q and q.strip():
        search = f"%{q.strip()}%"
        conditions.append(or_(JobDescriptionModel.title.ilike(search), JobDescriptionModel.company.ilike(search)))
    if source_type:
        conditions.append(JobDescriptionModel.source_type == source_type)
    if status:
        conditions.append(JobDescriptionModel.status == status)
    order = asc(JobDescriptionModel.updated_at) if direction == "asc" else desc(JobDescriptionModel.updated_at)
    result = await session.execute(
        select(
            JobDescriptionModel.id,
            JobDescriptionModel.title,
            JobDescriptionModel.company,
            JobDescriptionModel.location,
            JobDescriptionModel.source_type,
            JobDescriptionModel.status,
            JobDescriptionModel.processing_step,
            JobDescriptionModel.processing_error,
            JobDescriptionModel.seniority,
            JobDescriptionModel.updated_at,
            JobDescriptionModel.created_at,
        )
        .where(*conditions)
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total_statement = select(func.count()).select_from(JobDescriptionModel).where(*conditions)
    total = (await session.execute(total_statement)).scalar_one()
    items = [
        {
            "id": str(row.id),
            "title": row.title,
            "company": row.company,
            "location": row.location,
            "source_type": row.source_type,
            "status": row.status,
            "processing_step": row.processing_step,
            "processing_error": row.processing_error,
            "seniority": row.seniority,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.all()
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


async def get_jd_payload(session: AsyncSession, jd_id: uuid.UUID) -> dict[str, Any] | None:
    jd = await get_jd(session, jd_id)
    if jd is None:
        return None
    return serialize_jd(jd)


async def get_match_payload(session: AsyncSession, match_id: uuid.UUID) -> dict[str, Any] | None:
    row = await get_match(session, match_id)
    if row is None:
        return None
    return serialize_match(row)
