"""Application orchestration for initial job-search plan generation."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from backend.application.jd_service.matching import JDMatchingService
from backend.application.llm_config_service import get_active_verified_config
from backend.domain.jd.enums import JDStatus
from backend.domain.job_search_plan.enums import PlanStatus
from backend.domain.job_search_plan.policies import (
    PlanDomainError,
    build_source_catalog,
    generation_today,
    normalize_generated_tasks,
    sanitized_input_snapshot,
)
from backend.domain.job_search_plan.schemas import (
    CatalogEntry,
    PlanCreateRequest,
    PlanGenerationOutput,
    PlanPatchRequest,
)
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    JDMatchResultModel,
    JobDescriptionModel,
    JobSearchPlanModel,
    JobSearchPlanTaskModel,
    ResumeModel,
)
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.planners.llm_plan_generator import LLMPlanGenerationError, LLMPlanGenerator

UNFINISHED_PLAN_STATUSES = (
    PlanStatus.GENERATING.value,
    PlanStatus.REGENERATING.value,
    PlanStatus.ACTIVE.value,
    PlanStatus.FAILED.value,
)


@dataclass(frozen=True)
class PreparedPlanGeneration:
    plan_id: uuid.UUID
    run_id: uuid.UUID
    match_result_id: uuid.UUID
    input_snapshot: dict[str, object]
    model_name: str
    tasks: list[dict[str, object]]


async def get_fresh_match(
    session: AsyncSession,
    *,
    jd: JobDescriptionModel,
    resume_id: uuid.UUID,
) -> tuple[CandidateProfileModel, JDMatchResultModel]:
    """Reuse a match only when it is at least as new as both upstream documents."""
    profile = (
        await session.execute(
            select(CandidateProfileModel)
            .where(CandidateProfileModel.resume_id == resume_id)
            .options(noload(CandidateProfileModel.resume))
        )
    ).scalar_one_or_none()
    if profile is None:
        raise PlanDomainError("Resume does not have a candidate profile", 1008)
    latest = (
        await session.execute(
            select(JDMatchResultModel)
            .where(JDMatchResultModel.jd_id == jd.id, JDMatchResultModel.resume_id == resume_id)
            .order_by(JDMatchResultModel.created_at.desc())
            .limit(1)
            .options(noload(JDMatchResultModel.resume), noload(JDMatchResultModel.jd))
        )
    ).scalar_one_or_none()
    upstream_dates = [value for value in (jd.updated_at, profile.updated_at) if value is not None]
    stale = latest is None or any(latest.created_at < updated_at for updated_at in upstream_dates)
    if stale:
        latest = await JDMatchingService().match(session, resume_id, jd)
        await session.flush()
    assert latest is not None
    return profile, latest


async def generate_plan_output(
    session: AsyncSession,
    catalog: list[CatalogEntry],
    *,
    target_date,
    weekly_hours: int | None,
) -> tuple[PlanGenerationOutput, str]:
    """Use only the active verified database configuration for plan generation."""
    config = await get_active_verified_config(session)
    if config is None:
        await session.rollback()
        raise PlanDomainError("LLM not configured or not verified", 428)
    generator = LLMPlanGenerator(LLMGateway.from_config(config))
    # The gateway owns the decrypted configuration now. Release the database
    # transaction before the provider call, which can take the full task timeout.
    await session.rollback()
    output = await generator.generate(
        catalog,
        target_date=target_date.isoformat(),
        weekly_hours=weekly_hours or 8,
    )
    return output, generator.model_info


class PlanService:
    """Create/retry plans and perform external generation outside persistence locks."""

    async def create(self, session: AsyncSession, payload: PlanCreateRequest) -> JobSearchPlanModel:
        today = generation_today()
        if payload.target_date and (payload.target_date < today or payload.target_date > today + timedelta(days=365)):
            raise PlanDomainError("Target date must be within the next 365 days", 1001)
        jd = (
            await session.execute(
                select(JobDescriptionModel.title, JobDescriptionModel.company, JobDescriptionModel.status).where(
                    JobDescriptionModel.id == payload.jd_id
                )
            )
        ).one_or_none()
        if jd is None:
            raise PlanDomainError("Job description not found", 1002)
        if jd.status != JDStatus.READY.value:
            raise PlanDomainError("Job description must be ready", 1008)
        resume_id = (
            await session.execute(select(ResumeModel.id).where(ResumeModel.id == payload.resume_id))
        ).scalar_one_or_none()
        if resume_id is None:
            raise PlanDomainError("Resume not found", 1002)
        profile = (
            await session.execute(
                select(CandidateProfileModel.id).where(CandidateProfileModel.resume_id == payload.resume_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            raise PlanDomainError("Resume does not have a candidate profile", 1008)
        if await get_active_verified_config(session) is None:
            raise PlanDomainError("LLM not configured or not verified", 428)
        existing = await self._find_unfinished(session, payload.jd_id, payload.resume_id)
        if existing is not None:
            raise PlanDomainError(
                "An unfinished plan already exists for this job description and resume",
                1006,
                {"plan_id": str(existing.id)},
            )

        plan = JobSearchPlanModel(
            jd_id=payload.jd_id,
            resume_id=payload.resume_id,
            title=(
                payload.title.strip()
                if payload.title and payload.title.strip()
                else self._default_title(title=jd.title, company=jd.company)
            ),
            status=PlanStatus.GENERATING.value,
            target_date=payload.target_date,
            weekly_hours=payload.weekly_hours,
            supplemental_background=(payload.supplemental_background or "").strip() or None,
            generation_run_id=uuid.uuid4(),
            revision=0,
        )
        session.add(plan)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            if self._is_unfinished_plan_conflict(exc):
                existing = await self._find_unfinished(session, payload.jd_id, payload.resume_id)
                data = {"plan_id": str(existing.id)} if existing is not None else {}
                raise PlanDomainError("An unfinished plan already exists", 1006, data) from exc
            raise PlanDomainError("Plan inputs changed; refresh and retry", 1003) from exc
        return plan

    async def retry(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        expected_revision: int,
    ) -> JobSearchPlanModel:
        plan = (
            await session.execute(select(JobSearchPlanModel).where(JobSearchPlanModel.id == plan_id).with_for_update())
        ).scalar_one_or_none()
        if plan is None:
            raise PlanDomainError("Plan not found", 1002)
        if plan.status != PlanStatus.FAILED.value:
            raise PlanDomainError("Only failed plans can be retried", 1003)
        if plan.revision != expected_revision:
            raise PlanDomainError("Plan changed by another editor", 1007)
        if await get_active_verified_config(session) is None:
            raise PlanDomainError("LLM not configured or not verified", 428)
        plan.status = PlanStatus.GENERATING.value
        plan.generation_run_id = uuid.uuid4()
        plan.generation_error = None
        plan.revision += 1
        await session.commit()
        return plan

    async def patch(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        payload: PlanPatchRequest,
    ) -> JobSearchPlanModel:
        plan = (
            await session.execute(select(JobSearchPlanModel).where(JobSearchPlanModel.id == plan_id).with_for_update())
        ).scalar_one_or_none()
        if plan is None:
            raise PlanDomainError("Plan not found", 1002)
        if plan.status == PlanStatus.REGENERATING.value:
            raise PlanDomainError("Plan is regenerating", 1003)
        if plan.revision != payload.expected_revision:
            raise PlanDomainError("Plan changed by another editor", 1007)
        changed = set(payload.model_fields_set) - {"expected_revision"}
        if "title" in changed:
            if not payload.title or not payload.title.strip():
                raise PlanDomainError("Plan title cannot be empty", 1001)
            plan.title = payload.title.strip()
        if "target_date" in changed:
            today = generation_today()
            if payload.target_date and (
                payload.target_date < today or payload.target_date > today + timedelta(days=365)
            ):
                raise PlanDomainError("Target date must be within the next 365 days", 1001)
            plan.target_date = payload.target_date
        if "weekly_hours" in changed:
            plan.weekly_hours = payload.weekly_hours
        if "supplemental_background" in changed:
            plan.supplemental_background = (payload.supplemental_background or "").strip() or None
        if changed:
            plan.revision += 1
            await session.commit()
        return plan

    async def dispatch_initial(self, session: AsyncSession, plan: JobSearchPlanModel) -> bool:
        """Hand off an already-committed run; persist a safe state when broker handoff fails."""
        assert plan.generation_run_id is not None
        run_id = plan.generation_run_id
        try:
            from backend.tasks.plan_tasks import process_plan_generation

            await asyncio.to_thread(process_plan_generation, str(plan.id), str(run_id))
        except Exception:
            result = await session.execute(
                update(JobSearchPlanModel)
                .where(
                    JobSearchPlanModel.id == plan.id,
                    JobSearchPlanModel.generation_run_id == run_id,
                    JobSearchPlanModel.status == PlanStatus.GENERATING.value,
                )
                .values(
                    status=PlanStatus.FAILED.value,
                    generation_error="Unable to dispatch plan generation. Please retry.",
                    revision=JobSearchPlanModel.revision + 1,
                )
            )
            if getattr(result, "rowcount", 0) == 1:
                await session.commit()
                await session.refresh(plan)
            else:
                await session.rollback()
            return False
        return True

    async def prepare_generation(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> PreparedPlanGeneration | None:
        """Load minimized inputs and call the LLM without holding a row lock."""
        plan = await session.get(JobSearchPlanModel, plan_id)
        if plan is None or plan.generation_run_id != run_id:
            return None
        if plan.status not in {PlanStatus.GENERATING.value, PlanStatus.REGENERATING.value}:
            return None
        jd = await session.get(JobDescriptionModel, plan.jd_id)
        if jd is None or jd.status != JDStatus.READY.value:
            raise PlanDomainError("Job description must be ready", 1008)
        profile, match = await get_fresh_match(session, jd=jd, resume_id=plan.resume_id)
        await session.commit()
        effective_target = plan.target_date or generation_today() + timedelta(days=28)
        catalog = build_source_catalog(
            jd,
            profile,
            match,
            target_date=plan.target_date,
            weekly_hours=plan.weekly_hours,
            supplemental_background=plan.supplemental_background,
        )
        try:
            output, model_name = await generate_plan_output(
                session,
                catalog,
                target_date=effective_target,
                weekly_hours=plan.weekly_hours,
            )
        except LLMPlanGenerationError as exc:
            raise PlanDomainError("Plan generation returned invalid output", 5006) from exc
        return PreparedPlanGeneration(
            plan_id=plan.id,
            run_id=run_id,
            match_result_id=match.id,
            input_snapshot=sanitized_input_snapshot(
                catalog,
                match_id=match.id,
                target_date=plan.target_date,
                weekly_hours=plan.weekly_hours,
                supplemental_background=plan.supplemental_background,
                model_name=model_name,
            ),
            model_name=model_name,
            tasks=normalize_generated_tasks(output, catalog, target_date=plan.target_date),
        )

    async def persist_initial(self, session: AsyncSession, prepared: PreparedPlanGeneration) -> bool:
        """Atomically insert all initial tasks only when the run is still current."""
        plan = (
            await session.execute(
                select(JobSearchPlanModel).where(JobSearchPlanModel.id == prepared.plan_id).with_for_update()
            )
        ).scalar_one_or_none()
        if plan is None or plan.generation_run_id != prepared.run_id or plan.status != PlanStatus.GENERATING.value:
            await session.rollback()
            return False
        existing_count = (
            await session.execute(select(JobSearchPlanTaskModel.id).where(JobSearchPlanTaskModel.plan_id == plan.id))
        ).all()
        if existing_count:
            raise PlanDomainError("Initial plan run cannot replace existing tasks", 1003)
        for task in prepared.tasks:
            session.add(JobSearchPlanTaskModel(plan_id=plan.id, **task))
        plan.match_result_id = prepared.match_result_id
        plan.input_snapshot = prepared.input_snapshot
        plan.llm_model = prepared.model_name
        plan.generated_at = datetime.now(UTC)
        plan.generation_error = None
        plan.status = PlanStatus.ACTIVE.value
        plan.revision += 1
        await session.commit()
        return True

    async def mark_initial_failed(
        self,
        session: AsyncSession,
        *,
        plan_id: uuid.UUID,
        run_id: uuid.UUID,
        error: PlanDomainError | Exception,
    ) -> None:
        result = await session.execute(
            update(JobSearchPlanModel)
            .where(
                JobSearchPlanModel.id == plan_id,
                JobSearchPlanModel.generation_run_id == run_id,
                JobSearchPlanModel.status == PlanStatus.GENERATING.value,
            )
            .values(
                status=PlanStatus.FAILED.value,
                generation_error=str(error) if isinstance(error, PlanDomainError) else "Plan generation failed",
                revision=JobSearchPlanModel.revision + 1,
            )
        )
        if getattr(result, "rowcount", 0) != 1:
            await session.rollback()
            return
        await session.commit()

    async def _find_unfinished(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        resume_id: uuid.UUID,
    ) -> JobSearchPlanModel | None:
        return (
            await session.execute(
                select(JobSearchPlanModel)
                .where(
                    JobSearchPlanModel.jd_id == jd_id,
                    JobSearchPlanModel.resume_id == resume_id,
                    JobSearchPlanModel.status.in_(UNFINISHED_PLAN_STATUSES),
                )
                .order_by(JobSearchPlanModel.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    @staticmethod
    def _is_unfinished_plan_conflict(exc: IntegrityError) -> bool:
        diagnostic = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)
        return constraint_name == "uq_active_plan_jd_resume" or "uq_active_plan_jd_resume" in str(exc)

    @staticmethod
    def _default_title(*, title: str | None, company: str | None) -> str:
        if title and company:
            return f"{company} - {title} 求职计划"
        if title:
            return f"{title} 求职计划"
        return "求职计划"
