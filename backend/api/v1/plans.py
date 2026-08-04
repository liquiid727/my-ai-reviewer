"""Job-search plan API: generation lifecycle, tasks, revision conflicts, and recovery."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application.plan_regeneration_service import PlanRegenerationService
from backend.application.plan_service import PlanService
from backend.application.plan_task_service import PlanTaskService
from backend.domain.job_search_plan.enums import PlanStatus, PlanTaskStatus
from backend.domain.job_search_plan.schemas import (
    PlanCreateRequest,
    PlanPatchRequest,
    PlanRegenerateRequest,
    PlanRetryRequest,
    PlanTaskCreateRequest,
    PlanTaskOrderRequest,
    PlanTaskPatchRequest,
)
from backend.domain.job_search_plan.services import PlanDomainError
from backend.infrastructure.db.database import get_db
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    FileModel,
    JobDescriptionModel,
    JobSearchPlanModel,
    JobSearchPlanTaskModel,
    ResumeModel,
)

router = APIRouter(prefix="/plans", tags=["plans"])


def _error(exc: PlanDomainError) -> APIResponse:
    return APIResponse(code=exc.code, message=str(exc), data=exc.data or None)


def _task_to_dict(task: JobSearchPlanTaskModel) -> dict[str, Any]:
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


async def _is_generation_stale(session: AsyncSession, plan: JobSearchPlanModel) -> bool:
    if plan.generated_at is None:
        return False
    jd_updated_at = (
        await session.execute(
            select(JobDescriptionModel.updated_at).where(JobDescriptionModel.id == plan.jd_id)
        )
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


async def _detail_data(session: AsyncSession, plan: JobSearchPlanModel) -> dict[str, Any]:
    tasks = (
        await session.execute(
            select(JobSearchPlanTaskModel)
            .where(JobSearchPlanTaskModel.plan_id == plan.id)
            .order_by(JobSearchPlanTaskModel.sort_order, JobSearchPlanTaskModel.created_at)
        )
    ).scalars().all()
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
    return {
        "id": str(plan.id),
        "title": plan.title,
        "status": plan.status,
        "target_date": plan.target_date.isoformat() if plan.target_date else None,
        "weekly_hours": plan.weekly_hours,
        "supplemental_background": plan.supplemental_background,
        "revision": plan.revision,
        "generation_error": plan.generation_error,
        "generated_at": plan.generated_at.isoformat() if plan.generated_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        "is_generation_stale": await _is_generation_stale(session, plan),
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
        "tasks": [_task_to_dict(task) for task in tasks],
    }


@router.post("", response_model=APIResponse)
async def create_plan(
    payload: PlanCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    service = PlanService()
    try:
        plan = await service.create(session, payload)
        dispatched = await service.dispatch_initial(session, plan)
    except PlanDomainError as exc:
        return _error(exc)
    data = {
        "id": str(plan.id),
        "status": plan.status,
        "revision": plan.revision,
        "generation_error": plan.generation_error,
    }
    if not dispatched:
        return APIResponse(code=5004, message="Plan generation dispatch failed", data=data)
    return APIResponse(data=data)


@router.get("", response_model=APIResponse)
async def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    status: PlanStatus | None = None,
    direction: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
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
                "revision": row.plan_revision,
                "jd": {"title": row.jd_title, "company": row.jd_company},
                "resume": {"display_name": row.resume_name or f"Resume {str(row.resume_id)[:8]}"},
                "progress": {
                    "done": task_done,
                    "total": task_total,
                    "percent": round(task_done / task_total * 100) if task_total else 0,
                },
                "next_due_task": row.next_task_title,
                "updated_at": row.plan_updated_at.isoformat()
                if row.plan_updated_at
                else None,
            }
        )
    return APIResponse(data={"items": items, "page": page, "page_size": page_size, "total": total})


@router.post("/{plan_id}/retry", response_model=APIResponse)
async def retry_plan(
    plan_id: uuid.UUID,
    payload: PlanRetryRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    service = PlanService()
    try:
        plan = await service.retry(session, plan_id=plan_id, expected_revision=payload.expected_revision)
        dispatched = await service.dispatch_initial(session, plan)
    except PlanDomainError as exc:
        return _error(exc)
    data = {
        "id": str(plan.id),
        "status": plan.status,
        "revision": plan.revision,
        "generation_error": plan.generation_error,
    }
    if not dispatched:
        return APIResponse(code=5004, message="Plan generation dispatch failed", data=data)
    return APIResponse(data=data)


@router.post("/{plan_id}/regenerate", response_model=APIResponse)
async def regenerate_plan(
    plan_id: uuid.UUID,
    payload: PlanRegenerateRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    service = PlanRegenerationService()
    try:
        plan = await service.start(session, plan_id=plan_id, expected_revision=payload.expected_revision)
        dispatched = await service.dispatch(session, plan)
    except PlanDomainError as exc:
        return _error(exc)
    data = {
        "id": str(plan.id),
        "status": plan.status,
        "revision": plan.revision,
        "generation_error": plan.generation_error,
    }
    if not dispatched:
        return APIResponse(code=5004, message="Plan regeneration dispatch failed", data=data)
    return APIResponse(data=data)


@router.post("/{plan_id}/tasks", response_model=APIResponse)
async def create_plan_task(
    plan_id: uuid.UUID,
    payload: PlanTaskCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        plan, task, progress = await PlanTaskService().create(session, plan_id=plan_id, payload=payload)
    except PlanDomainError as exc:
        return _error(exc)
    return APIResponse(data={"task": _task_to_dict(task), "revision": plan.revision, "progress": progress.model_dump()})


@router.patch("/{plan_id}/tasks/{task_id}", response_model=APIResponse)
async def patch_plan_task(
    plan_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: PlanTaskPatchRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        plan, task, progress = await PlanTaskService().patch(
            session, plan_id=plan_id, task_id=task_id, payload=payload
        )
    except PlanDomainError as exc:
        return _error(exc)
    return APIResponse(data={"task": _task_to_dict(task), "revision": plan.revision, "progress": progress.model_dump()})


@router.delete("/{plan_id}/tasks/{task_id}", response_model=APIResponse)
async def delete_plan_task(
    plan_id: uuid.UUID,
    task_id: uuid.UUID,
    expected_revision: int = Query(..., ge=0),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        plan, progress = await PlanTaskService().delete(
            session,
            plan_id=plan_id,
            task_id=task_id,
            expected_revision=expected_revision,
        )
    except PlanDomainError as exc:
        return _error(exc)
    return APIResponse(data={"revision": plan.revision, "progress": progress.model_dump()})


@router.put("/{plan_id}/tasks/order", response_model=APIResponse)
async def reorder_plan_tasks(
    plan_id: uuid.UUID,
    payload: PlanTaskOrderRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        plan, progress = await PlanTaskService().reorder(session, plan_id=plan_id, payload=payload)
    except PlanDomainError as exc:
        return _error(exc)
    return APIResponse(data={"revision": plan.revision, "progress": progress.model_dump()})


@router.get("/{plan_id}", response_model=APIResponse)
async def get_plan(plan_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    plan = await session.get(JobSearchPlanModel, plan_id)
    if plan is None:
        return APIResponse(code=1002, message="Plan not found")
    return APIResponse(data=await _detail_data(session, plan))


@router.patch("/{plan_id}", response_model=APIResponse)
async def patch_plan(
    plan_id: uuid.UUID,
    payload: PlanPatchRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        plan = await PlanService().patch(session, plan_id=plan_id, payload=payload)
    except PlanDomainError as exc:
        return _error(exc)
    return APIResponse(data=await _detail_data(session, plan))


@router.delete("/{plan_id}", response_model=APIResponse)
async def delete_plan(
    plan_id: uuid.UUID,
    expected_revision: int = Query(..., ge=0),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        await PlanRegenerationService().delete(session, plan_id, expected_revision)
    except PlanDomainError as exc:
        return _error(exc)
    return APIResponse(message="Plan deleted")
