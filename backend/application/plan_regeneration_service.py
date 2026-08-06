"""Atomic replacement of unfinished AI tasks while preserving user work."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.llm_config_service import get_active_verified_config
from backend.application.plan_service import UNFINISHED_PLAN_STATUSES, PreparedPlanGeneration
from backend.application.plan_task_service import MAX_PLAN_TASKS
from backend.domain.jd.enums import JDStatus
from backend.domain.job_search_plan.enums import PlanStatus, PlanTaskSource, PlanTaskStatus
from backend.domain.job_search_plan.policies import PlanDomainError
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    JobDescriptionModel,
    JobSearchPlanModel,
    JobSearchPlanTaskModel,
)


class PlanRegenerationService:
    """Protect completed/manual rows and replace only unfinished AI output."""

    async def start(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        expected_revision: int,
    ) -> JobSearchPlanModel:
        plan = await self._lock_plan(session, plan_id)
        if plan.revision != expected_revision:
            raise PlanDomainError("Plan changed by another editor", 1007)
        if plan.status not in {PlanStatus.ACTIVE.value, PlanStatus.COMPLETED.value}:
            raise PlanDomainError("Plan cannot be regenerated in its current state", 1003)
        jd_status = (
            await session.execute(select(JobDescriptionModel.status).where(JobDescriptionModel.id == plan.jd_id))
        ).scalar_one_or_none()
        if jd_status != JDStatus.READY.value:
            raise PlanDomainError("Job description must be ready", 1008)
        profile = (
            await session.execute(
                select(CandidateProfileModel.id).where(CandidateProfileModel.resume_id == plan.resume_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            raise PlanDomainError("Resume does not have a candidate profile", 1008)
        if await get_active_verified_config(session) is None:
            raise PlanDomainError("LLM not configured or not verified", 428)
        conflict = (
            await session.execute(
                select(JobSearchPlanModel.id)
                .where(
                    JobSearchPlanModel.id != plan.id,
                    JobSearchPlanModel.jd_id == plan.jd_id,
                    JobSearchPlanModel.resume_id == plan.resume_id,
                    JobSearchPlanModel.status.in_(UNFINISHED_PLAN_STATUSES),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if conflict is not None:
            raise PlanDomainError("Another unfinished plan already exists", 1006, {"plan_id": str(conflict)})
        plan.previous_status = plan.status
        plan.status = PlanStatus.REGENERATING.value
        plan.generation_run_id = uuid.uuid4()
        plan.generation_error = None
        plan.revision += 1
        await session.commit()
        return plan

    async def dispatch(self, session: AsyncSession, plan: JobSearchPlanModel) -> bool:
        assert plan.generation_run_id is not None
        try:
            from backend.tasks.plan_tasks import process_plan_regeneration

            await asyncio.to_thread(process_plan_regeneration, str(plan.id), str(plan.generation_run_id))
        except Exception:
            await self.mark_failed(
                session,
                plan_id=plan.id,
                run_id=plan.generation_run_id,
                error=PlanDomainError("Unable to dispatch plan regeneration. Please retry.", 5004),
            )
            return False
        return True

    async def persist(self, session: AsyncSession, prepared: PreparedPlanGeneration) -> bool:
        plan = await self._lock_plan(session, prepared.plan_id)
        if plan.generation_run_id != prepared.run_id or plan.status != PlanStatus.REGENERATING.value:
            await session.rollback()
            return False
        tasks = (
            (
                await session.execute(
                    select(JobSearchPlanTaskModel)
                    .where(JobSearchPlanTaskModel.plan_id == plan.id)
                    .order_by(JobSearchPlanTaskModel.sort_order)
                )
            )
            .scalars()
            .all()
        )
        preserved = [
            task
            for task in tasks
            if task.source == PlanTaskSource.MANUAL.value or task.status == PlanTaskStatus.DONE.value
        ]
        if len(preserved) + len(prepared.tasks) > MAX_PLAN_TASKS:
            raise PlanDomainError("Regeneration would exceed the 200-task plan limit", 1009)
        await session.execute(
            delete(JobSearchPlanTaskModel).where(
                JobSearchPlanTaskModel.plan_id == plan.id,
                JobSearchPlanTaskModel.source == PlanTaskSource.AI.value,
                JobSearchPlanTaskModel.status != PlanTaskStatus.DONE.value,
            )
        )
        max_order = max((task.sort_order for task in preserved), default=-1)
        for index, task in enumerate(prepared.tasks, max_order + 1):
            values = {key: value for key, value in task.items() if key != "sort_order"}
            session.add(JobSearchPlanTaskModel(plan_id=plan.id, sort_order=index, **values))
        plan.match_result_id = prepared.match_result_id
        match_snapshot = prepared.input_snapshot.get("match") if isinstance(prepared.input_snapshot, dict) else None
        if isinstance(match_snapshot, dict):
            plan.match_input_fingerprint = match_snapshot.get("input_fingerprint")  # type: ignore[assignment]
            plan.match_stale_reasons = []
        plan.input_snapshot = prepared.input_snapshot
        plan.llm_model = prepared.model_name
        plan.generated_at = datetime.now(UTC)
        plan.generation_error = None
        plan.previous_status = None
        plan.status = PlanStatus.ACTIVE.value
        plan.revision += 1
        await session.commit()
        return True

    async def mark_failed(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        run_id: uuid.UUID,
        error: PlanDomainError | Exception,
    ) -> None:
        try:
            plan = await self._lock_plan(session, plan_id)
        except PlanDomainError as exc:
            # A deleted plan is a stale worker result, not a new worker failure.
            if exc.code == 1002:
                return
            raise
        if plan.generation_run_id != run_id or plan.status != PlanStatus.REGENERATING.value:
            return
        plan.status = plan.previous_status or PlanStatus.ACTIVE.value
        plan.previous_status = None
        plan.generation_error = str(error) if isinstance(error, PlanDomainError) else "Plan regeneration failed"
        plan.revision += 1
        await session.commit()

    async def delete(self, session: AsyncSession, plan_id: uuid.UUID, expected_revision: int) -> None:
        plan = await self._lock_plan(session, plan_id)
        if plan.revision != expected_revision:
            raise PlanDomainError("Plan changed by another editor", 1007)
        plan.generation_run_id = uuid.uuid4()
        await session.delete(plan)
        await session.commit()

    @staticmethod
    async def _lock_plan(session: AsyncSession, plan_id: uuid.UUID) -> JobSearchPlanModel:
        plan = (
            await session.execute(select(JobSearchPlanModel).where(JobSearchPlanModel.id == plan_id).with_for_update())
        ).scalar_one_or_none()
        if plan is None:
            raise PlanDomainError("Plan not found", 1002)
        return plan
