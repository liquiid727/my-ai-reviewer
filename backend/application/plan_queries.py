"""Plan read-side use cases (list/detail/eligible resumes)."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_matching.freshness import current_match_fingerprint, stale_reasons
from backend.domain.job_search_plan.enums import PlanStatus, PlanTaskStatus
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    FileModel,
    JDMatchResultModel,
    JobDescriptionModel,
    JobSearchPlanModel,
    JobSearchPlanTaskModel,
    ResumeModel,
)


def task_to_dict(task: JobSearchPlanTaskModel) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "plan_id": str(task.plan_id),
        "title": task.title,
        "category": task.category,
        "description": task.description,
        "basis": task.basis or [],
        "source": task.source,
        "priority": task.priority,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "sort_order": task.sort_order,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


async def is_generation_stale(session: AsyncSession, plan: JobSearchPlanModel) -> bool:
    if plan.generated_at is None:
        return False
    jd_updated_at = (
        await session.execute(select(JobDescriptionModel.updated_at).where(JobDescriptionModel.id == plan.jd_id))
    ).scalar_one_or_none()
    profile = (
        await session.execute(
            select(CandidateProfileModel.updated_at).where(CandidateProfileModel.resume_id == plan.resume_id)
        )
    ).scalar_one_or_none()
    if jd_updated_at and jd_updated_at > plan.generated_at:
        return True
    if profile is not None and profile > plan.generated_at:
        return True
    preferences = (plan.input_snapshot or {}).get("preferences", {})
    if not isinstance(preferences, dict):
        return True
    return preferences != {
        "target_date": plan.target_date.isoformat() if plan.target_date else None,
        "weekly_hours": plan.weekly_hours,
        "supplemental_background": plan.supplemental_background or None,
    }


async def _plan_match_payload(session: AsyncSession, plan: JobSearchPlanModel) -> dict[str, Any] | None:
    if plan.match_result_id is None:
        return None
    match = await session.get(JDMatchResultModel, plan.match_result_id)
    if match is None:
        return None
    profile = (
        await session.execute(select(CandidateProfileModel).where(CandidateProfileModel.resume_id == plan.resume_id))
    ).scalar_one_or_none()
    jd = await session.get(JobDescriptionModel, plan.jd_id)
    expected = None
    reasons = ["result_failed_or_incomplete"]
    if jd is not None and profile is not None:
        expected = current_match_fingerprint(
            jd=jd, profile=profile, provider=match.provider, model_name=match.model_name
        )
        reasons = stale_reasons(
            match, expected_fingerprint=expected, provider=match.provider, model_name=match.model_name
        )
    return {
        "id": str(match.id),
        "mode": match.mode,
        "input_fingerprint": match.input_fingerprint,
        "fresh": not reasons,
        "stale_reasons": reasons,
        "matcher_version": match.matcher_version,
        "hard_filter_policy_version": match.hard_filter_policy_version,
        "prompt_version": match.prompt_version,
        "schema_version": match.schema_version,
        "provider": match.provider,
        "model": match.model_name,
        "expected_fingerprint": expected,
    }


async def build_detail_payload(session: AsyncSession, plan: JobSearchPlanModel) -> dict[str, Any]:
    tasks = (
        (
            await session.execute(
                select(JobSearchPlanTaskModel)
                .where(JobSearchPlanTaskModel.plan_id == plan.id)
                .order_by(JobSearchPlanTaskModel.sort_order, JobSearchPlanTaskModel.created_at)
            )
        )
        .scalars()
        .all()
    )
    total = len(tasks)
    done = sum(task.status == PlanTaskStatus.DONE.value for task in tasks)
    jd = (
        await session.execute(
            select(JobDescriptionModel.title, JobDescriptionModel.company).where(JobDescriptionModel.id == plan.jd_id)
        )
    ).one_or_none()
    resume_row = (
        await session.execute(
            select(ResumeModel.id, FileModel.original_name)
            .outerjoin(FileModel, FileModel.id == ResumeModel.file_id)
            .where(ResumeModel.id == plan.resume_id)
        )
    ).first()
    match_payload = await _plan_match_payload(session, plan)
    return {
        "id": str(plan.id),
        "title": plan.title,
        "status": plan.status,
        "input_contract": "versioned" if plan.job_target_id is not None else "legacy",
        "job_target_id": str(plan.job_target_id) if plan.job_target_id else None,
        "jd_version_id": str(plan.jd_version_id) if plan.jd_version_id else None,
        "resume_version_id": str(plan.resume_version_id) if plan.resume_version_id else None,
        "match_assessment_id": str(plan.match_assessment_id) if plan.match_assessment_id else None,
        "target_date": plan.target_date.isoformat() if plan.target_date else None,
        "weekly_hours": plan.weekly_hours,
        "supplemental_background": plan.supplemental_background,
        "revision": plan.revision,
        "generation_error": plan.generation_error,
        "generated_at": plan.generated_at.isoformat() if plan.generated_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        "is_generation_stale": await is_generation_stale(session, plan),
        "match": match_payload,
        "progress": {"done": done, "total": total, "percent": round(done / total * 100) if total else 0},
        "jd": {
            "id": str(plan.jd_id),
            "title": jd.title if jd else None,
            "company": jd.company if jd else None,
        },
        "resume": {
            "id": str(plan.resume_id),
            "display_name": (resume_row.original_name if resume_row else None) or f"Resume {str(plan.resume_id)[:8]}",
        },
        "tasks": [task_to_dict(task) for task in tasks],
    }


async def get_plan(session: AsyncSession, plan_id: object) -> JobSearchPlanModel | None:
    return await session.get(JobSearchPlanModel, plan_id)


async def list_plans_payload(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    q: str | None,
    status: PlanStatus | None,
    direction: Literal["asc", "desc"],
) -> dict[str, Any]:
    task_stats = (
        select(
            JobSearchPlanTaskModel.plan_id.label("plan_id"),
            func.count(JobSearchPlanTaskModel.id).label("total"),
            func.coalesce(
                func.sum(case((JobSearchPlanTaskModel.status == PlanTaskStatus.DONE.value, 1), else_=0)), 0
            ).label("done"),
        )
        .group_by(JobSearchPlanTaskModel.plan_id)
        .subquery()
    )
    next_task_title = (
        select(JobSearchPlanTaskModel.title)
        .where(
            JobSearchPlanTaskModel.plan_id == JobSearchPlanModel.id,
            JobSearchPlanTaskModel.status != PlanTaskStatus.DONE.value,
        )
        .order_by(
            JobSearchPlanTaskModel.due_date.is_(None),
            JobSearchPlanTaskModel.due_date,
            JobSearchPlanTaskModel.sort_order,
        )
        .limit(1)
        .scalar_subquery()
    )
    conditions: list[Any] = []
    if q and q.strip():
        search = f"%{q.strip()}%"
        conditions.append(
            or_(
                JobSearchPlanModel.title.ilike(search),
                JobDescriptionModel.title.ilike(search),
                JobDescriptionModel.company.ilike(search),
            )
        )
    if status is not None:
        conditions.append(JobSearchPlanModel.status == status.value)
    ordering = JobSearchPlanModel.updated_at.asc() if direction == "asc" else JobSearchPlanModel.updated_at.desc()
    statement = (
        select(
            JobSearchPlanModel.id.label("plan_id"),
            JobSearchPlanModel.resume_id.label("resume_id"),
            JobSearchPlanModel.title.label("plan_title"),
            JobSearchPlanModel.status.label("plan_status"),
            JobSearchPlanModel.revision.label("plan_revision"),
            JobSearchPlanModel.job_target_id.label("job_target_id"),
            JobSearchPlanModel.updated_at.label("plan_updated_at"),
            JobDescriptionModel.title.label("jd_title"),
            JobDescriptionModel.company.label("jd_company"),
            FileModel.original_name.label("resume_name"),
            func.coalesce(task_stats.c.total, 0).label("task_total"),
            func.coalesce(task_stats.c.done, 0).label("task_done"),
            next_task_title.label("next_task_title"),
        )
        .join(JobDescriptionModel, JobDescriptionModel.id == JobSearchPlanModel.jd_id)
        .join(ResumeModel, ResumeModel.id == JobSearchPlanModel.resume_id)
        .outerjoin(FileModel, FileModel.id == ResumeModel.file_id)
        .outerjoin(task_stats, task_stats.c.plan_id == JobSearchPlanModel.id)
        .where(*conditions)
        .order_by(ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(statement)).all()
    total = (
        await session.execute(
            select(func.count())
            .select_from(JobSearchPlanModel)
            .join(JobDescriptionModel, JobDescriptionModel.id == JobSearchPlanModel.jd_id)
            .where(*conditions)
        )
    ).scalar_one()
    items = []
    for row in rows:
        task_total = int(row.task_total)
        task_done = int(row.task_done)
        items.append(
            {
                "id": str(row.plan_id),
                "title": row.plan_title,
                "status": row.plan_status,
                "input_contract": "versioned" if row.job_target_id is not None else "legacy",
                "revision": row.plan_revision,
                "jd": {"title": row.jd_title, "company": row.jd_company},
                "resume": {"display_name": row.resume_name or f"Resume {str(row.resume_id)[:8]}"},
                "progress": {
                    "done": task_done,
                    "total": task_total,
                    "percent": round(task_done / task_total * 100) if task_total else 0,
                },
                "next_due_task": row.next_task_title,
                "updated_at": row.plan_updated_at.isoformat() if row.plan_updated_at else None,
            }
        )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


async def get_eligible_resume_options(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, object]], int]:
    """Select only resume option fields; never hydrate profile identity/raw resume text."""
    statement = (
        select(ResumeModel.id, ResumeModel.updated_at, FileModel.original_name)
        .join(CandidateProfileModel, CandidateProfileModel.resume_id == ResumeModel.id)
        .outerjoin(FileModel, FileModel.id == ResumeModel.file_id)
        .order_by(ResumeModel.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(statement)).all()
    total = (
        await session.execute(
            select(func.count())
            .select_from(ResumeModel)
            .join(CandidateProfileModel, CandidateProfileModel.resume_id == ResumeModel.id)
        )
    ).scalar_one()
    return (
        [
            {
                "id": str(row.id),
                "display_name": row.original_name or f"Resume {str(row.id)[:8]}",
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
        int(total),
    )
