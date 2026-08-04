"""Transactional task mutations guarded by one plan-level revision."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job_search_plan.enums import PlanStatus, PlanTaskSource, PlanTaskStatus
from backend.domain.job_search_plan.schemas import (
    PlanProgress,
    PlanTaskCreateRequest,
    PlanTaskOrderRequest,
    PlanTaskPatchRequest,
)
from backend.domain.job_search_plan.services import PlanDomainError
from backend.infrastructure.db.models import JobSearchPlanModel, JobSearchPlanTaskModel

MAX_PLAN_TASKS = 200


class PlanTaskService:
    """Perform every task mutation in the same transaction as the revision increment."""

    async def create(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        payload: PlanTaskCreateRequest,
    ) -> tuple[JobSearchPlanModel, JobSearchPlanTaskModel, PlanProgress]:
        plan = await self._lock_mutable_plan(session, plan_id, payload.expected_revision)
        count = (
            await session.execute(
                select(func.count())
                .select_from(JobSearchPlanTaskModel)
                .where(JobSearchPlanTaskModel.plan_id == plan.id)
            )
        ).scalar_one()
        if count >= MAX_PLAN_TASKS:
            raise PlanDomainError("Plan cannot contain more than 200 tasks", 1009)
        title = payload.title.strip()
        if not title:
            raise PlanDomainError("Task title cannot be empty", 1001)
        max_order = (
            await session.execute(
                select(func.max(JobSearchPlanTaskModel.sort_order)).where(JobSearchPlanTaskModel.plan_id == plan.id)
            )
        ).scalar_one()
        task = JobSearchPlanTaskModel(
            plan_id=plan.id,
            title=title,
            category=payload.category.value,
            description=payload.description.strip(),
            basis=[],
            source=PlanTaskSource.MANUAL.value,
            priority=payload.priority.value,
            status=payload.status.value,
            due_date=payload.due_date,
            sort_order=(max_order if max_order is not None else -1) + 1,
        )
        session.add(task)
        await session.flush()
        progress = await self._refresh_progress_and_status(session, plan)
        plan.revision += 1
        await session.commit()
        return plan, task, progress

    async def patch(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        task_id: uuid.UUID,
        payload: PlanTaskPatchRequest,
    ) -> tuple[JobSearchPlanModel, JobSearchPlanTaskModel, PlanProgress]:
        plan = await self._lock_mutable_plan(session, plan_id, payload.expected_revision)
        task = await session.get(JobSearchPlanTaskModel, task_id)
        if task is None or task.plan_id != plan.id:
            raise PlanDomainError("Plan task not found", 1002)
        changed = set(payload.model_fields_set) - {"expected_revision"}
        for field in changed:
            value = getattr(payload, field)
            if field != "due_date" and value is None:
                raise PlanDomainError(f"{field} cannot be null", 1001)
            if field in {"category", "priority", "status"} and value is not None:
                value = value.value
            if field in {"title", "description"} and value is not None:
                value = value.strip()
            if field == "title" and not value:
                raise PlanDomainError("Task title cannot be empty", 1001)
            setattr(task, field, value)
        await session.flush()
        progress = await self._refresh_progress_and_status(session, plan)
        if changed:
            plan.revision += 1
        await session.commit()
        return plan, task, progress

    async def delete(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        task_id: uuid.UUID,
        expected_revision: int,
    ) -> tuple[JobSearchPlanModel, PlanProgress]:
        plan = await self._lock_mutable_plan(session, plan_id, expected_revision)
        task = await session.get(JobSearchPlanTaskModel, task_id)
        if task is None or task.plan_id != plan.id:
            raise PlanDomainError("Plan task not found", 1002)
        if task.status == PlanTaskStatus.DONE.value:
            raise PlanDomainError("Reopen a completed task before deleting it", 1003)
        await session.delete(task)
        await session.flush()
        progress = await self._refresh_progress_and_status(session, plan)
        plan.revision += 1
        await session.commit()
        return plan, progress

    async def reorder(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        payload: PlanTaskOrderRequest,
    ) -> tuple[JobSearchPlanModel, PlanProgress]:
        plan = await self._lock_mutable_plan(session, plan_id, payload.expected_revision)
        if len(payload.task_ids) != len(set(payload.task_ids)):
            raise PlanDomainError("Task order cannot contain duplicate IDs", 1009)
        tasks = (
            await session.execute(
                select(JobSearchPlanTaskModel).where(JobSearchPlanTaskModel.plan_id == plan.id)
            )
        ).scalars().all()
        existing_ids = {task.id for task in tasks}
        if existing_ids != set(payload.task_ids) or len(tasks) != len(payload.task_ids):
            raise PlanDomainError("Task order must contain every current task exactly once", 1009)
        by_id = {task.id: task for task in tasks}
        for sort_order, task_id in enumerate(payload.task_ids):
            by_id[task_id].sort_order = sort_order
        progress = await self._refresh_progress_and_status(session, plan)
        plan.revision += 1
        await session.commit()
        return plan, progress

    async def progress(self, session: AsyncSession, plan_id: uuid.UUID) -> PlanProgress:
        statuses = (
            await session.execute(
                select(JobSearchPlanTaskModel.status).where(JobSearchPlanTaskModel.plan_id == plan_id)
            )
        ).scalars().all()
        return self._progress_from_statuses(statuses)

    async def _lock_mutable_plan(
        self,
        session: AsyncSession,
        plan_id: uuid.UUID,
        expected_revision: int,
    ) -> JobSearchPlanModel:
        plan = (
            await session.execute(
                select(JobSearchPlanModel).where(JobSearchPlanModel.id == plan_id).with_for_update()
            )
        ).scalar_one_or_none()
        if plan is None:
            raise PlanDomainError("Plan not found", 1002)
        if plan.status == PlanStatus.REGENERATING.value:
            raise PlanDomainError("Plan is regenerating; task mutations are temporarily disabled", 1003)
        if plan.status not in {PlanStatus.ACTIVE.value, PlanStatus.COMPLETED.value}:
            raise PlanDomainError("Plan is not ready for task edits", 1003)
        if plan.revision != expected_revision:
            raise PlanDomainError("Plan changed by another editor", 1007)
        return plan

    async def _refresh_progress_and_status(
        self,
        session: AsyncSession,
        plan: JobSearchPlanModel,
    ) -> PlanProgress:
        statuses = (
            await session.execute(
                select(JobSearchPlanTaskModel.status).where(JobSearchPlanTaskModel.plan_id == plan.id)
            )
        ).scalars().all()
        progress = self._progress_from_statuses(statuses)
        if progress.total > 0 and progress.done == progress.total:
            plan.status = PlanStatus.COMPLETED.value
        else:
            plan.status = PlanStatus.ACTIVE.value
        return progress

    @staticmethod
    def _progress_from_statuses(statuses: Sequence[str]) -> PlanProgress:
        total = len(statuses)
        done = sum(status == PlanTaskStatus.DONE.value for status in statuses)
        percent = round(done / total * 100) if total else 0
        return PlanProgress(done=done, total=total, percent=percent)
