"""Match Assessment application commands/queries and worker use cases (RIP-013 §7, §9).

The create command is idempotent: it validates exact versions, ensures the
active Job Target, reuses a completed result for the same tuple unless
`force=true`, and otherwise persists a `queued` row and dispatches the
worker only after commit. The worker builds the Source Catalog, runs the
constrained semantic classifier through the LLM gateway + PrivacyGuard,
and finalizes one immutable completed result under current run ownership.
No external call holds a database transaction.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.job_target import (
    EnsureTargetCommand,
    JobTargetNotFoundError,
    JobTargetUseCases,
    TargetResult,
)
from backend.application.llm_config_service import get_active_verified_config
from backend.domain.match_assessment import report as report_rules
from backend.domain.match_assessment.engine import evaluate
from backend.domain.match_assessment.lifecycle import (
    Failure,
    MatchAssessmentState,
    MatchAssessmentTuple,
    MatchLifecycle,
    MatchLifecycleError,
)
from backend.domain.match_assessment.policy import POLICY_VERSION
from backend.domain.match_assessment.schemas import DimensionInput, GapInput
from backend.domain.match_assessment.source_catalog import build_catalog
from backend.infrastructure.db.models import (
    JobDescriptionModel,
    JobDescriptionVersionModel,
    JobTargetModel,
    MatchAssessmentModel,
    ResumeVersionModel,
)
from backend.infrastructure.matchers import (
    ALLOWED_DIMENSIONS,
    ConstrainedSemanticMatcher,
    MatchSemanticError,
)

logger = logging.getLogger(__name__)

POLICY_SUPPORTED = ("match-v1",)


class MatchAssessmentError(Exception):
    """Base Match Assessment application error."""


class AssessmentVersionNotFoundError(MatchAssessmentError):
    """One immutable version does not exist."""


class AssessmentInputNotReadyError(MatchAssessmentError):
    """One immutable version is unavailable (not ready / privacy ineligible)."""


class AssessmentNotFoundError(MatchAssessmentError):
    """No assessment with this id."""


class AssessmentUnsupportedPolicyError(MatchAssessmentError):
    """The requested policy version is not supported."""


@dataclass(frozen=True)
class CreateAssessmentCommand:
    job_target_id: uuid.UUID | None = None
    jd_version_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    policy_version: str = POLICY_VERSION
    force: bool = False


@dataclass(frozen=True)
class CreateAssessmentResult:
    id: uuid.UUID
    job_target_id: uuid.UUID
    jd_version_id: uuid.UUID
    resume_version_id: uuid.UUID
    status: str
    run_id: uuid.UUID
    attempt: int
    reused: bool
    created: bool
    policy_version: str
    error_code: str | None = None
    error_details: str | None = None
    retryable: bool = False


def created_payload(result: CreateAssessmentResult) -> dict[str, Any]:
    """API-facing payload for create/retry; safe fields only (RIP-013 §9)."""
    return {
        "id": str(result.id),
        "job_target_id": str(result.job_target_id),
        "jd_version_id": str(result.jd_version_id),
        "resume_version_id": str(result.resume_version_id),
        "status": result.status,
        "policy_version": result.policy_version,
        "run_id": str(result.run_id),
        "attempt": result.attempt,
        "reused": result.reused,
        "created": result.created,
        "error_code": result.error_code,
        "error_details": result.error_details,
        "retryable": result.retryable,
    }


def assessment_payload(
    assessment: MatchAssessmentModel,
    *,
    reused: bool = False,
) -> dict[str, Any]:
    """API-facing detail payload; never provider raw output or unmasked content."""
    return {
        "id": str(assessment.id),
        "job_target_id": str(assessment.job_target_id),
        "jd_version_id": str(assessment.jd_version_id),
        "resume_version_id": str(assessment.resume_version_id),
        "status": assessment.status,
        "policy_version": assessment.policy_version,
        "run_id": str(assessment.run_id),
        "attempt": assessment.attempt,
        "reused": reused,
        "error_code": assessment.error_code,
        "error_details": assessment.error_details,
        "retryable": assessment.retryable,
        "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
        "updated_at": assessment.updated_at.isoformat() if assessment.updated_at else None,
        "completed_at": assessment.completed_at.isoformat() if assessment.completed_at else None,
        "result": _result_payload(assessment) if assessment.status == "completed" else None,
    }


def _result_payload(assessment: MatchAssessmentModel) -> dict[str, Any]:
    return {
        "policy_version": assessment.policy_version,
        "schema_version": assessment.schema_version,
        "total_score": _num(assessment.total_score),
        "score_before_caps": _num(assessment.score_before_caps),
        "overall_confidence": _num(assessment.overall_confidence),
        "recommendation": assessment.recommendation,
        "caps_applied": assessment.caps_applied or [],
        "dimension_scores": assessment.dimension_scores or [],
        "rule_results": assessment.rule_results or [],
        "gaps": assessment.gaps or [],
        "evidence_summary": assessment.evidence_summary or {},
        "model_name": assessment.model_name,
        "model_version": assessment.model_version,
        "prompt_version": assessment.prompt_version,
    }


def _num(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _state_from_model(row: MatchAssessmentModel) -> MatchAssessmentState:
    return MatchAssessmentState(
        id=row.id,
        job_target_id=row.job_target_id,
        jd_version_id=row.jd_version_id,
        resume_version_id=row.resume_version_id,
        status=row.status,
        policy_version=row.policy_version,
        run_id=row.run_id,
        attempt=row.attempt,
        retryable=bool(row.retryable),
        total_score=row.total_score,
        completed_at=row.completed_at,
    )


class MatchAssessmentUseCases:
    """Idempotent create/reuse/force and retry commands."""

    def __init__(self) -> None:
        self._lifecycle = MatchLifecycle()

    async def create(
        self,
        session: AsyncSession,
        command: CreateAssessmentCommand,
    ) -> CreateAssessmentResult:
        """Validate versions, ensure the active target, reuse or queue + dispatch."""
        if command.policy_version not in POLICY_SUPPORTED:
            raise AssessmentUnsupportedPolicyError(
                f"unsupported policy_version {command.policy_version}"
            )
        jd_version, resume_version = await self._load_versions(
            session, command.jd_version_id, command.resume_version_id
        )
        target = await self._ensure_target(session, command.job_target_id, jd_version)
        self._lifecycle.validate_scope(
            target_jd_id=target.job_description_id,
            jd_version_owner=jd_version.job_description_id,
        )

        tuple_ = MatchAssessmentTuple(
            job_target_id=target.id,
            jd_version_id=jd_version.id,
            resume_version_id=resume_version.id,
            policy_version=command.policy_version,
        )
        existing = await self._latest_for_tuple(session, tuple_)
        reuse, run_id = self._lifecycle.pick_create(
            tuple_=tuple_, existing=existing, force=command.force
        )
        if reuse:
            assert existing is not None
            return CreateAssessmentResult(
                id=existing.id,
                job_target_id=existing.job_target_id,
                jd_version_id=existing.jd_version_id,
                resume_version_id=existing.resume_version_id,
                status=existing.status,
                run_id=existing.run_id,
                attempt=existing.attempt,
                reused=True,
                created=False,
                policy_version=existing.policy_version,
            )

        assessment = MatchAssessmentModel(
            id=uuid.uuid4(),
            job_target_id=target.id,
            jd_version_id=jd_version.id,
            resume_version_id=resume_version.id,
            status="queued",
            policy_version=command.policy_version,
            run_id=run_id,
            attempt=1,
            retryable=False,
        )
        session.add(assessment)
        await session.commit()
        await session.refresh(assessment)
        dispatched = await self._dispatch(session, assessment)
        if not dispatched:
            await self._mark_broker_failed(session, assessment.id)
            await session.refresh(assessment)
        return CreateAssessmentResult(
            id=assessment.id,
            job_target_id=assessment.job_target_id,
            jd_version_id=assessment.jd_version_id,
            resume_version_id=assessment.resume_version_id,
            status=assessment.status,
            run_id=assessment.run_id,
            attempt=assessment.attempt,
            reused=False,
            created=True,
            policy_version=assessment.policy_version,
            error_code=assessment.error_code,
            error_details=assessment.error_details,
            retryable=bool(assessment.retryable),
        )

    async def retry(
        self,
        session: AsyncSession,
        assessment_id: uuid.UUID,
    ) -> CreateAssessmentResult:
        """Retry a failed assessment: new run id on the same row, then requeue."""
        row = await session.get(MatchAssessmentModel, assessment_id)
        if row is None:
            raise AssessmentNotFoundError(f"assessment {assessment_id} not found")
        state = _state_from_model(row)
        new_run, attempt = self._lifecycle.retry(state)
        row.status = "queued"
        row.run_id = new_run
        row.attempt = attempt
        row.error_code = None
        row.error_details = None
        row.retryable = False
        await session.commit()
        await session.refresh(row)
        dispatched = await self._dispatch(session, row)
        if not dispatched:
            await self._mark_broker_failed(session, row.id)
            await session.refresh(row)
        return CreateAssessmentResult(
            id=row.id,
            job_target_id=row.job_target_id,
            jd_version_id=row.jd_version_id,
            resume_version_id=row.resume_version_id,
            status=row.status,
            run_id=row.run_id,
            attempt=row.attempt,
            reused=False,
            created=False,
            policy_version=row.policy_version,
            error_code=row.error_code,
            error_details=row.error_details,
            retryable=bool(row.retryable),
        )

    async def _load_versions(
        self,
        session: AsyncSession,
        jd_version_id: uuid.UUID | None,
        resume_version_id: uuid.UUID | None,
    ) -> tuple[JobDescriptionVersionModel, ResumeVersionModel]:
        if jd_version_id is None or resume_version_id is None:
            raise AssessmentVersionNotFoundError(
                "jd_version_id and resume_version_id are required"
            )
        jd_version = await session.get(JobDescriptionVersionModel, jd_version_id)
        resume_version = await session.get(ResumeVersionModel, resume_version_id)
        if jd_version is None or resume_version is None:
            raise AssessmentVersionNotFoundError("one of the immutable versions does not exist")
        return jd_version, resume_version

    async def _ensure_target(
        self,
        session: AsyncSession,
        job_target_id: uuid.UUID | None,
        jd_version: JobDescriptionVersionModel,
    ) -> TargetResult:
        if job_target_id is not None:
            try:
                return await JobTargetUseCases().get(session, job_target_id)
            except JobTargetNotFoundError as exc:
                raise AssessmentInputNotReadyError(str(exc)) from exc
        try:
            return await JobTargetUseCases().ensure(
                session,
                EnsureTargetCommand(jd_id=jd_version.job_description_id),
            )
        except JobTargetNotFoundError as exc:  # pragma: no cover - defensive
            raise AssessmentInputNotReadyError(str(exc)) from exc

    async def _latest_for_tuple(
        self,
        session: AsyncSession,
        tuple_: MatchAssessmentTuple,
    ) -> MatchAssessmentState | None:
        stmt = (
            select(MatchAssessmentModel)
            .where(
                MatchAssessmentModel.jd_version_id == tuple_.jd_version_id,
                MatchAssessmentModel.resume_version_id == tuple_.resume_version_id,
                MatchAssessmentModel.policy_version == tuple_.policy_version,
            )
            .order_by(
                MatchAssessmentModel.created_at.desc(),
                MatchAssessmentModel.id.desc(),
            )
            .limit(1)
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        return _state_from_model(row) if row is not None else None

    async def _dispatch(self, session: AsyncSession, row: MatchAssessmentModel) -> bool:
        try:
            from backend.tasks.match_tasks import process_match_assessment

            await asyncio.to_thread(process_match_assessment, str(row.id), str(row.run_id))
            return True
        except Exception:
            logger.exception("match assessment dispatch failed for %s", row.id)
            return False

    async def _mark_broker_failed(self, session: AsyncSession, assessment_id: uuid.UUID) -> None:
        await session.execute(
            update(MatchAssessmentModel)
            .where(MatchAssessmentModel.id == assessment_id)
            .values(
                status="failed",
                error_code="ASSESSMENT_DEPENDENCY_TIMEOUT",
                error_details="broker dispatch failed; safe retryable diagnostic",
                retryable=True,
            )
        )
        await session.commit()


class MatchAssessmentQueries:
    """Cursor list and immutable detail reads (RIP-013 §9)."""

    async def get(
        self,
        session: AsyncSession,
        assessment_id: uuid.UUID,
    ) -> MatchAssessmentModel:
        # populate_existing: the row may be in the identity map with expired
        # server-side attributes (worker commits with expire_on_commit=False);
        # the detail endpoint must always reflect the committed row.
        row = await session.get(
            MatchAssessmentModel, assessment_id, populate_existing=True
        )
        if row is None:
            raise AssessmentNotFoundError(f"assessment {assessment_id} not found")
        return row

    async def list(
        self,
        session: AsyncSession,
        *,
        job_target_id: uuid.UUID | None = None,
        jd_version_id: uuid.UUID | None = None,
        resume_version_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        before_created_at: datetime | None = None,
        before_id: uuid.UUID | None = None,
    ) -> tuple[list[MatchAssessmentModel], bool]:
        """Newest-first cursor list; returns (rows, has_more).

        Fetches limit+1 rows so the caller can emit a terminal cursor: when
        fewer rows than the limit come back, the page is exhausted.
        """
        stmt = select(MatchAssessmentModel)
        if job_target_id is not None:
            stmt = stmt.where(MatchAssessmentModel.job_target_id == job_target_id)
        if jd_version_id is not None:
            stmt = stmt.where(MatchAssessmentModel.jd_version_id == jd_version_id)
        if resume_version_id is not None:
            stmt = stmt.where(MatchAssessmentModel.resume_version_id == resume_version_id)
        if status is not None:
            stmt = stmt.where(MatchAssessmentModel.status == status)
        if before_created_at is not None and before_id is not None:
            stmt = stmt.where(
                (MatchAssessmentModel.created_at < before_created_at)
                | (
                    (MatchAssessmentModel.created_at == before_created_at)
                    & (MatchAssessmentModel.id < before_id)
                )
            )
        elif before_created_at is not None:
            stmt = stmt.where(MatchAssessmentModel.created_at < before_created_at)
        stmt = stmt.order_by(
            MatchAssessmentModel.created_at.desc(),
            MatchAssessmentModel.id.desc(),
        ).limit(max(1, min(limit, 100)) + 1)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        return (rows[:limit], has_more)


def report_payload(
    *,
    assessment: MatchAssessmentModel,
    jd_version: JobDescriptionVersionModel | None,
    resume_version: ResumeVersionModel | None,
    target: JobTargetModel | None,
    jd: JobDescriptionModel | None,
) -> dict[str, Any]:
    """RIP-014 §6.1 report projection; safe public fields only.

    The completed result is returned as evaluated (immutable). Staleness is
    advisory metadata about current versions — it never replaces the report's
    pinned version identities.
    """
    dimensions = assessment.dimension_scores or []
    gaps = assessment.gaps or []
    catalog_ids: set[str] = set()
    if jd_version is not None and resume_version is not None:
        catalog = build_catalog(
            jd_version_id=str(jd_version.id),
            jd_structured=jd_version.structured or {},
            resume_version_id=str(resume_version.id),
            resume_profile=resume_version.profile_snapshot or {},
            resume_facts=resume_version.evidence_catalog or [],
        )
        catalog_ids = catalog.ids()

    return {
        "version_facts": {
            "policy_version": assessment.policy_version,
            "schema_version": assessment.schema_version,
            "jd_version_id": str(assessment.jd_version_id),
            "resume_version_id": str(assessment.resume_version_id),
            "jd_version_no": jd_version.version_no if jd_version is not None else None,
            "resume_version_source_type": (
                resume_version.source_type if resume_version is not None else None
            ),
        },
        "scores": {
            "total_score": _num(assessment.total_score),
            "score_before_caps": _num(assessment.score_before_caps),
            "caps_applied": assessment.caps_applied or [],
            "overall_confidence": _num(assessment.overall_confidence),
            "recommendation": assessment.recommendation,
        },
        "dimensions": dimensions,
        "gap_classes": report_rules.gap_class_counts(gaps),
        "evidence_sufficiency": report_rules.evidence_sufficiency(
            assessment.evidence_summary or {},
            dimensions,
            catalog_ids,
        ),
        "explicit_unknowns": [
            {"kind": "evidence_citation", "evidence_id": item}
            for item in report_rules.evidence_sufficiency(
                assessment.evidence_summary or {},
                dimensions,
                catalog_ids,
            )["unknown_citations"]
        ],
        "stale": report_rules.stale_versions(
            jd_version_id=str(assessment.jd_version_id),
            resume_version_id=str(assessment.resume_version_id),
            current_jd_version_id=(
                str(jd.current_version_id)
                if jd is not None and jd.current_version_id is not None
                else None
            ),
            target_default_jd_version_id=(
                str(target.default_jd_version_id)
                if target is not None and target.default_jd_version_id is not None
                else None
            ),
            target_default_resume_version_id=(
                str(target.default_resume_version_id)
                if target is not None and target.default_resume_version_id is not None
                else None
            ),
        ),
        "actions": report_rules.action_routes(
            resume_version_id=str(assessment.resume_version_id),
            resume_version_source_type=(
                resume_version.source_type if resume_version is not None else None
            ),
            parsed_resume_id=(
                str(resume_version.resume_id) if resume_version is not None else None
            ),
            builder_draft_id=(
                str(resume_version.draft_id) if resume_version is not None else None
            ),
        ),
        "model": {
            "name": assessment.model_name,
            "version": assessment.model_version,
            "prompt_version": assessment.prompt_version,
        },
        "completed_at": (
            assessment.completed_at.isoformat() if assessment.completed_at else None
        ),
    }


class MatchReportQueries:
    """One batched read for the completed report projection (RIP-014 §7.1)."""

    async def report(
        self,
        session: AsyncSession,
        assessment_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        row = await session.get(
            MatchAssessmentModel, assessment_id, populate_existing=True
        )
        if row is None:
            return None
        if row.status != "completed":
            return None
        return await self._build(session, row)

    async def _build(
        self,
        session: AsyncSession,
        row: MatchAssessmentModel,
    ) -> dict[str, Any]:
        stmt = (
            select(
                JobDescriptionVersionModel,
                ResumeVersionModel,
                JobTargetModel,
                JobDescriptionModel,
            )
            .select_from(JobTargetModel)
            .join(
                JobDescriptionModel,
                JobDescriptionModel.id == JobTargetModel.job_description_id,
            )
            .outerjoin(
                JobDescriptionVersionModel,
                JobDescriptionVersionModel.id == row.jd_version_id,
            )
            .outerjoin(
                ResumeVersionModel,
                ResumeVersionModel.id == row.resume_version_id,
            )
            .where(JobTargetModel.id == row.job_target_id)
        )
        fetched = (await session.execute(stmt)).first()
        if fetched is None:
            return {}
        jd_version, resume_version, target, jd = fetched
        return report_payload(
            assessment=row,
            jd_version=jd_version,
            resume_version=resume_version,
            target=target,
            jd=jd,
        )


class MatchAssessmentWorker:
    """Celery worker stages: evaluate under current run ownership (RIP-013 §7.1)."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        matcher: ConstrainedSemanticMatcher | None = None,
    ) -> None:
        self._session = session
        self._matcher = matcher
        self._lifecycle = MatchLifecycle()

    async def evaluate(self, assessment_id: uuid.UUID, run_id: uuid.UUID) -> str:
        row = await self._session.get(MatchAssessmentModel, assessment_id)
        if row is None:
            return "missing"
        state = _state_from_model(row)
        if run_id != state.run_id or state.status != "queued":
            return "stale"

        row.status = "evaluating"
        await self._session.commit()
        try:
            result, model_info = await self._run_pipeline(row)
        except MatchSemanticError as exc:
            await self._persist_failure(
                row,
                run_id,
                Failure(
                    code="ASSESSMENT_EVIDENCE_INVALID" if exc.evidence_invalid else "ASSESSMENT_FAILED",
                    details=str(exc),
                    retryable=exc.retryable,
                ),
            )
            return "failed"
        except TimeoutError:
            await self._persist_failure(
                row,
                run_id,
                Failure(
                    code="ASSESSMENT_DEPENDENCY_TIMEOUT",
                    details="bounded external call timed out",
                    retryable=True,
                ),
            )
            return "failed"
        except Exception:
            logger.exception("match assessment %s failed", assessment_id)
            await self._persist_failure(
                row,
                run_id,
                Failure(code="ASSESSMENT_FAILED", details="safe terminal failure", retryable=False),
            )
            return "failed"

        current = _state_from_model(row)
        try:
            self._lifecycle.complete(current, run_id=run_id)
        except MatchLifecycleError:
            return "stale"
        row.status = "completed"
        row.completed_at = _utcnow()
        row.model_name = model_info
        row.total_score = _to_decimal(result.total_score, 2)
        row.score_before_caps = _to_decimal(result.score_before_caps, 2)
        row.overall_confidence = _to_decimal(result.overall_confidence, 3)
        row.recommendation = result.recommendation
        row.caps_applied = list(result.caps_applied)
        row.dimension_scores = [d.model_dump() for d in result.dimensions]
        row.rule_results = _flatten_rule_results(result.dimensions)
        row.gaps = [g.model_dump() for g in result.gaps]
        row.evidence_summary = dict(result.evidence_summary)
        row.schema_version = result.schema_version
        await self._session.commit()
        return "completed"

    async def _run_pipeline(
        self,
        row: MatchAssessmentModel,
    ) -> tuple[Any, str]:
        jd_version = await self._session.get(JobDescriptionVersionModel, row.jd_version_id)
        resume_version = await self._session.get(ResumeVersionModel, row.resume_version_id)
        if jd_version is None or resume_version is None:
            raise MatchSemanticError("input version no longer available", evidence_invalid=True)

        catalog = build_catalog(
            jd_version_id=str(jd_version.id),
            jd_structured=jd_version.structured,
            resume_version_id=str(resume_version.id),
            resume_profile=resume_version.profile_snapshot,
            resume_facts=resume_version.evidence_catalog,
        )
        requirements = _requirement_ids(jd_version.structured, catalog)

        matcher = self._matcher
        if matcher is None:
            config = await get_active_verified_config(self._session)
            if config is None:
                await self._session.rollback()
                raise MatchSemanticError("LLM not configured or not verified")
            matcher = ConstrainedSemanticMatcher(_gateway_from_config(config))
            # The gateway owns the decrypted configuration now. Release the
            # transaction before the provider call, which can take the full
            # task timeout (RIP-013 7.1: no external call holds a transaction).
            await self._session.rollback()

        semantic = await matcher.classify(
            catalog=catalog,
            dimensions=list(ALLOWED_DIMENSIONS),
            requirements=requirements,
        )
        result = evaluate(
            dimension_inputs=[
                DimensionInput(
                    key=dim.key,
                    raw_score=dim.raw_score,
                    confidence=dim.confidence,
                    cited_jd_evidence=list(dim.cited_jd_evidence),
                    cited_resume_evidence=list(dim.cited_resume_evidence),
                    explanation=dim.explanation,
                )
                for dim in semantic.dimensions
            ],
            gaps=[
                GapInput(
                    requirement_id=gap.requirement_id,
                    category=gap.category,
                    severity=gap.severity,  # type: ignore[arg-type]
                    candidate_evidence=list(gap.candidate_evidence),
                    missing_evidence=gap.missing_evidence,
                    confidence=gap.confidence,
                    uncertain=gap.uncertain,
                )
                for gap in semantic.gaps
            ],
        )
        return result, semantic.model_info or ""

    async def _persist_failure(
        self,
        row: MatchAssessmentModel,
        run_id: uuid.UUID,
        failure: Failure,
    ) -> None:
        current = _state_from_model(row)
        try:
            self._lifecycle.fail(current, run_id=run_id, failure=failure)
        except MatchLifecycleError:
            return
        row.status = "failed"
        row.error_code = failure.code
        row.error_details = failure.details
        row.retryable = failure.retryable
        await self._session.commit()


def _gateway_from_config(config: Any) -> Any:
    from backend.infrastructure.llm.gateway import LLMGateway

    return LLMGateway.from_config(config)


def _requirement_ids(structured: dict[str, Any], catalog: Any) -> list[str]:
    """Requirement catalog IDs in structured order, restricted to the catalog."""
    ids: list[str] = []
    version = _jd_version_from_items(catalog)
    for index, item in enumerate(structured.get("required_skills") or []):
        if not isinstance(item, dict):
            continue
        key = item.get("key") or f"req-{index}"
        candidate = f"jd:{version}:requirement:{key}"
        if candidate in catalog.ids():
            ids.append(candidate)
    return ids


def _jd_version_from_items(catalog: Any) -> str:
    for item in catalog.items:
        if item.id.startswith("jd:"):
            parts = item.id.split(":")
            if len(parts) >= 3:
                return parts[1]
    return ""


def _flatten_rule_results(dimensions: list[Any]) -> list[Any]:
    results: list[Any] = []
    for dim in dimensions:
        for rule in getattr(dim, "rule_results", []) or []:
            results.append(rule.model_dump())
    return results


def _to_decimal(value: float, places: int) -> Decimal:
    return Decimal(str(round(value, places)))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
