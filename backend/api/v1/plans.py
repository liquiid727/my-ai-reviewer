"""Job-search plan API: generation lifecycle, tasks, revision conflicts, and recovery."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application import plan_queries
from backend.application.plan_regeneration_service import PlanRegenerationService
from backend.application.plan_service import PlanService
from backend.application.plan_task_service import PlanTaskService
from backend.domain.job_search_plan.enums import PlanStatus
from backend.domain.job_search_plan.policies import PlanDomainError, PlanVersionTupleError
from backend.domain.job_search_plan.schemas import (
    PlanCreateRequest,
    PlanPatchRequest,
    PlanRegenerateRequest,
    PlanRetryRequest,
    PlanTaskCreateRequest,
    PlanTaskOrderRequest,
    PlanTaskPatchRequest,
)
from backend.infrastructure.db.database import get_db

router = APIRouter(prefix="/plans", tags=["plans"])


def _error(exc: PlanDomainError) -> APIResponse:
    return APIResponse(code=exc.code, message=str(exc), data=exc.data or None)


def _versioned_error(exc: PlanVersionTupleError) -> APIResponse:
    if exc.kind == "assessment":
        return APIResponse(code=1006, message=str(exc))
    return APIResponse(code=1001, message=str(exc))


@router.post("", response_model=APIResponse)
async def create_plan(
    payload: PlanCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    service = PlanService()
    try:
        plan = await service.create(session, payload)
        dispatched = await service.dispatch_initial(session, plan)
    except PlanVersionTupleError as exc:
        return _versioned_error(exc)
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
    data = await plan_queries.list_plans_payload(
        session,
        page=page,
        page_size=page_size,
        q=q,
        status=status,
        direction=direction,
    )
    return APIResponse(data=data)


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
    return APIResponse(
        data={"task": plan_queries.task_to_dict(task), "revision": plan.revision, "progress": progress.model_dump()}
    )


@router.patch("/{plan_id}/tasks/{task_id}", response_model=APIResponse)
async def patch_plan_task(
    plan_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: PlanTaskPatchRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        plan, task, progress = await PlanTaskService().patch(session, plan_id=plan_id, task_id=task_id, payload=payload)
    except PlanDomainError as exc:
        return _error(exc)
    return APIResponse(
        data={"task": plan_queries.task_to_dict(task), "revision": plan.revision, "progress": progress.model_dump()}
    )


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
    plan = await plan_queries.get_plan(session, plan_id)
    if plan is None:
        return APIResponse(code=1002, message="Plan not found")
    return APIResponse(data=await plan_queries.build_detail_payload(session, plan))


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
    return APIResponse(data=await plan_queries.build_detail_payload(session, plan))


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
