"""Application orchestration for initial job-search plan generation."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from backend.application.jd_matching.service import HybridJDMatchingService
from backend.application.jd_service.matching import JDMatchingService
from backend.application.llm_config_service import get_active_verified_config
from backend.domain.jd.enums import JDStatus
from backend.domain.jd.matching_v2 import MatchStatus
from backend.domain.job_search_plan.enums import PlanStatus
from backend.domain.job_search_plan.policies import (
    VERSIONED_PLAN_REF_KEYS,
    PlanDomainError,
    PlanVersionTupleError,
    build_catalog_from_versions,
    build_source_catalog,
    generation_today,
    normalize_generated_tasks,
    sanitized_input_snapshot,
    validate_versioned_tuple,
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
    JobDescriptionVersionModel,
    JobSearchPlanModel,
    JobSearchPlanTaskModel,
    MatchAssessmentModel,
    ResumeModel,
    ResumeVersionModel,
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
    match_result_id: uuid.UUID | None
    input_snapshot: dict[str, object]
    model_name: str
    tasks: list[dict[str, object]]


@dataclass(frozen=True)
class VersionedPlanRefs:
    """Validated version-pinned tuple written with the plan's initial transaction."""

    target_id: uuid.UUID
    jd_version_id: uuid.UUID
    resume_version_id: uuid.UUID
    match_assessment_id: uuid.UUID


async def get_fresh_match(
    session: AsyncSession,
    *,
    jd: JobDescriptionModel,
    resume_id: uuid.UUID,
) -> tuple[CandidateProfileModel, JDMatchResultModel]:
    """Prefer fingerprint-fresh hybrid_v2 results; fall back to rules_v1 only for compatibility."""
    profile = (
        await session.execute(
            select(CandidateProfileModel)
            .where(CandidateProfileModel.resume_id == resume_id)
            .options(noload(CandidateProfileModel.resume))
        )
    ).scalar_one_or_none()
    if profile is None:
        raise PlanDomainError("Resume does not have a candidate profile", 1008)
    config = await get_active_verified_config(session)
    provider = getattr(config, "provider", None) if config is not None else None
    model_name = getattr(config, "model_name", None) if config is not None else None
    from backend.application.jd_matching.freshness import current_match_fingerprint, is_fresh
    from backend.domain.jd.matching_v2 import MatchMode

    expected = current_match_fingerprint(jd=jd, profile=profile, provider=provider, model_name=model_name)
    latest = (
        await session.execute(
            select(JDMatchResultModel)
            .where(
                JDMatchResultModel.jd_id == jd.id,
                JDMatchResultModel.resume_id == resume_id,
                JDMatchResultModel.mode == MatchMode.HYBRID_V2.value,
            )
            .order_by(JDMatchResultModel.created_at.desc())
            .limit(1)
            .options(noload(JDMatchResultModel.resume), noload(JDMatchResultModel.jd))
        )
    ).scalar_one_or_none()
    if latest is not None and is_fresh(latest, expected_fingerprint=expected, provider=provider, model_name=model_name):
        return profile, latest
    if config is not None:
        run = await HybridJDMatchingService().create_match(
            session,
            jd_id=jd.id,
            resume_id=resume_id,
            force=latest is not None,
            dispatch=False,
        )
        active = await session.get(JDMatchResultModel, run.id)
        if active is not None and active.processing_run_id is not None:
            try:
                await HybridJDMatchingService().run_match(session, active.id, active.processing_run_id)
            except Exception:
                pass
            await session.refresh(active)
            if active.status == MatchStatus.READY.value:
                return profile, active
    legacy = await JDMatchingService().match(session, resume_id, jd)
    await session.flush()
    return profile, legacy


async def generate_plan_output(
    session: AsyncSession,
    catalog: list[CatalogEntry],
    *,
    target_date: date,
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


def _match_snapshot(match: JDMatchResultModel) -> dict[str, object]:
    return {
        "match_result_id": str(match.id),
        "mode": getattr(match, "mode", "rules_v1"),
        "input_fingerprint": getattr(match, "input_fingerprint", None),
        "matcher_version": getattr(match, "matcher_version", None),
        "hard_filter_policy_version": getattr(match, "hard_filter_policy_version", None),
        "prompt_version": getattr(match, "prompt_version", None),
        "schema_version": getattr(match, "schema_version", None),
        "provider": getattr(match, "provider", None),
        "model": getattr(match, "model_name", None),
        "dimensions": (getattr(match, "dimension_scores", None) or [])[:7],
        "evidence_summary": (getattr(match, "evidence", None) or [])[:20],
    }


class PlanService:
    """Create/retry plans and perform external generation outside persistence locks."""

    async def create(self, session: AsyncSession, payload: PlanCreateRequest) -> JobSearchPlanModel:
        today = generation_today()
        if payload.target_date and (payload.target_date < today or payload.target_date > today + timedelta(days=365)):
            raise PlanDomainError("Target date must be within the next 365 days", 1001)
        version_pinned = self._version_pinned_refs(payload)
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
        versioned = await self._validate_versioned_inputs(session, payload, version_pinned) if version_pinned else None
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
            job_target_id=versioned.target_id if versioned is not None else None,
            jd_version_id=versioned.jd_version_id if versioned is not None else None,
            resume_version_id=versioned.resume_version_id if versioned is not None else None,
            match_assessment_id=versioned.match_assessment_id if versioned is not None else None,
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
            if self._is_versioned_plan_conflict(exc):
                raise PlanDomainError("A version-pinned unfinished plan already exists", 1006) from exc
            raise PlanDomainError("Plan inputs changed; refresh and retry", 1003) from exc
        return plan

    @staticmethod
    def _version_pinned_refs(payload: PlanCreateRequest) -> dict[str, uuid.UUID] | None:
        refs = {key: getattr(payload, key) for key in VERSIONED_PLAN_REF_KEYS if getattr(payload, key) is not None}
        if not refs:
            return None
        missing = [key for key in VERSIONED_PLAN_REF_KEYS if getattr(payload, key) is None]
        if missing:
            raise PlanDomainError(
                f"Version-pinned plan requires all of: {', '.join(VERSIONED_PLAN_REF_KEYS)}",
                1001,
            )
        return refs

    async def _validate_versioned_inputs(
        self,
        session: AsyncSession,
        payload: PlanCreateRequest,
        refs: dict[str, uuid.UUID],
    ) -> VersionedPlanRefs:
        """One coherent tuple: target identity, exact versions, completed assessment."""
        jd_version = await session.get(JobDescriptionVersionModel, refs["jd_version_id"])
        resume_version = await session.get(ResumeVersionModel, refs["resume_version_id"])
        if jd_version is None:
            raise PlanVersionTupleError("JD version does not exist", "scope")
        if resume_version is None:
            raise PlanVersionTupleError("Resume version does not exist", "scope")
        if jd_version.job_description_id != payload.jd_id:
            raise PlanVersionTupleError("JD version does not belong to the selected JD", "scope")
        if resume_version.resume_id != payload.resume_id:
            raise PlanVersionTupleError("Resume version does not belong to the selected resume", "scope")
        from backend.application.job_target import JobTargetNotFoundError, JobTargetUseCases

        try:
            target = await JobTargetUseCases().get(session, refs["job_target_id"])
        except JobTargetNotFoundError as exc:
            raise PlanVersionTupleError("Job target does not exist", "scope") from exc
        assessment = await session.get(MatchAssessmentModel, refs["match_assessment_id"])
        validate_versioned_tuple(
            target_id=target.id,
            target_jd_id=target.job_description_id,
            target_resume_id=payload.resume_id,
            jd_version_owner=jd_version.job_description_id,
            resume_version_owner=resume_version.resume_id,
            assessment_status=assessment.status if assessment is not None else None,
            assessment_target_id=(assessment.job_target_id if assessment is not None else None),
            assessment_jd_version_id=(assessment.jd_version_id if assessment is not None else None),
            assessment_resume_version_id=(assessment.resume_version_id if assessment is not None else None),
            requested_match_assessment_id=refs["match_assessment_id"],
            requested_jd_version_id=refs["jd_version_id"],
            requested_resume_version_id=refs["resume_version_id"],
        )
        return VersionedPlanRefs(
            target_id=refs["job_target_id"],
            jd_version_id=refs["jd_version_id"],
            resume_version_id=refs["resume_version_id"],
            match_assessment_id=refs["match_assessment_id"],
        )

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
        if plan.job_target_id is not None:
            catalog = await self._catalog_from_versions(session, plan)
            # Versioned provenance lives on match_assessment_id; this legacy
            # column is a jd_match_results FK, so it must stay NULL here.
            match_id = None
        else:
            catalog = build_source_catalog(
                jd,
                profile,
                match,
                target_date=plan.target_date,
                weekly_hours=plan.weekly_hours,
                supplemental_background=plan.supplemental_background,
            )
            match_id = match.id
        await session.commit()
        effective_target = plan.target_date or generation_today() + timedelta(days=28)
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
            match_result_id=match_id,
            input_snapshot={
                **sanitized_input_snapshot(
                    catalog,
                    match_id=match_id,
                    target_date=plan.target_date,
                    weekly_hours=plan.weekly_hours,
                    supplemental_background=plan.supplemental_background,
                    model_name=model_name,
                ),
                "match": _match_snapshot(match),
            },
            model_name=model_name,
            tasks=normalize_generated_tasks(output, catalog, target_date=plan.target_date),
        )

    async def _catalog_from_versions(
        self,
        session: AsyncSession,
        plan: JobSearchPlanModel,
    ) -> list[CatalogEntry]:
        """Deterministic catalog from the plan's immutable snapshots (RIP-014 §6.2).

        The tuple was validated at create time; the assessment and versions
        are immutable, so regeneration retains the original versions.
        """
        jd_version = await session.get(JobDescriptionVersionModel, plan.jd_version_id)
        resume_version = await session.get(ResumeVersionModel, plan.resume_version_id)
        assessment = await session.get(MatchAssessmentModel, plan.match_assessment_id)
        if jd_version is None or resume_version is None or assessment is None:
            raise PlanDomainError("Plan input versions are no longer available", 1008)
        return build_catalog_from_versions(
            jd_version_id=str(jd_version.id),
            jd_structured=jd_version.structured,
            resume_version_id=str(resume_version.id),
            resume_profile=resume_version.profile_snapshot,
            resume_facts=resume_version.evidence_catalog,
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
        match_snapshot = prepared.input_snapshot.get("match") if isinstance(prepared.input_snapshot, dict) else None
        if isinstance(match_snapshot, dict):
            plan.match_input_fingerprint = str(match_snapshot.get("input_fingerprint") or "") or None
            plan.match_stale_reasons = []
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
    def _is_versioned_plan_conflict(exc: IntegrityError) -> bool:
        diagnostic = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)
        return constraint_name == "uq_versioned_plan_tuple" or "uq_versioned_plan_tuple" in str(exc)

    @staticmethod
    def _default_title(*, title: str | None, company: str | None) -> str:
        if title and company:
            return f"{company} - {title} 求职计划"
        if title:
            return f"{title} 求职计划"
        return "求职计划"
