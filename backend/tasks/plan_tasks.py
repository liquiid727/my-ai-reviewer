"""Celery handoff for initial job-search plan generation."""

from __future__ import annotations

import uuid
from typing import Any

from backend.application.plan_regeneration_service import PlanRegenerationService
from backend.application.plan_service import PlanService
from backend.celery_app import celery
from backend.domain.job_search_plan.policies import PlanDomainError
from backend.infrastructure.db.celery_database import celery_async_session_factory as async_session_factory
from backend.tasks.async_runtime import run_async


async def _perform_initial(plan_id: uuid.UUID, run_id: uuid.UUID) -> str:
    async with async_session_factory() as session:
        service = PlanService()
        prepared = await service.prepare_generation(session, plan_id=plan_id, run_id=run_id)
        if prepared is None:
            return "stale"
        persisted = await service.persist_initial(session, prepared)
        return "active" if persisted else "stale"


async def _mark_initial_failed(plan_id: uuid.UUID, run_id: uuid.UUID, error: Exception) -> None:
    async with async_session_factory() as session:
        await PlanService().mark_initial_failed(session, plan_id=plan_id, run_id=run_id, error=error)


async def _perform_regeneration(plan_id: uuid.UUID, run_id: uuid.UUID) -> str:
    async with async_session_factory() as session:
        generation_service = PlanService()
        prepared = await generation_service.prepare_generation(session, plan_id=plan_id, run_id=run_id)
        if prepared is None:
            return "stale"
        persisted = await PlanRegenerationService().persist(session, prepared)
        return "active" if persisted else "stale"


async def _mark_regeneration_failed(plan_id: uuid.UUID, run_id: uuid.UUID, error: Exception) -> None:
    async with async_session_factory() as session:
        await PlanRegenerationService().mark_failed(session, plan_id=plan_id, run_id=run_id, error=error)


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.plan_generate",
    time_limit=180,
    max_retries=2,
    default_retry_delay=30,
)
def plan_generation_task(self: Any, plan_id_str: str, run_id_str: str) -> str:
    """Generate once per task attempt; only the current run may persist results."""
    plan_id = uuid.UUID(plan_id_str)
    run_id = uuid.UUID(run_id_str)
    try:
        return run_async(_perform_initial(plan_id, run_id))
    except PlanDomainError as exc:
        if exc.code == 428:
            run_async(_mark_initial_failed(plan_id, run_id, exc))
            return "failed"
        if self.request.retries >= (self.max_retries or 0):
            run_async(_mark_initial_failed(plan_id, run_id, exc))
            return "failed"
        raise self.retry(exc=exc)
    except Exception:
        safe_error = PlanDomainError("Plan generation failed", 5001)
        if self.request.retries >= (self.max_retries or 0):
            run_async(_mark_initial_failed(plan_id, run_id, safe_error))
            return "failed"
        raise self.retry(exc=safe_error)


def process_plan_generation(plan_id: str, run_id: str) -> None:
    plan_generation_task.apply_async(args=(plan_id, run_id))


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.plan_regenerate",
    time_limit=180,
    max_retries=2,
    default_retry_delay=30,
)
def plan_regeneration_task(self: Any, plan_id_str: str, run_id_str: str) -> str:
    plan_id = uuid.UUID(plan_id_str)
    run_id = uuid.UUID(run_id_str)
    try:
        return run_async(_perform_regeneration(plan_id, run_id))
    except PlanDomainError as exc:
        if exc.code == 428:
            run_async(_mark_regeneration_failed(plan_id, run_id, exc))
            return "failed"
        if self.request.retries >= (self.max_retries or 0):
            run_async(_mark_regeneration_failed(plan_id, run_id, exc))
            return "failed"
        raise self.retry(exc=exc)
    except Exception:
        safe_error = PlanDomainError("Plan regeneration failed", 5001)
        if self.request.retries >= (self.max_retries or 0):
            run_async(_mark_regeneration_failed(plan_id, run_id, safe_error))
            return "failed"
        raise self.retry(exc=safe_error)


def process_plan_regeneration(plan_id: str, run_id: str) -> None:
    plan_regeneration_task.apply_async(args=(plan_id, run_id))
