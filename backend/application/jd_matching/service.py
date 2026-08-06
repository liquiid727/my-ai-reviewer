"""Hybrid v2 JD matching use case."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from backend.application.jd_matching.catalog import build_match_source_catalog
from backend.application.jd_matching.freshness import (
    current_match_fingerprint,
    fingerprint_parts,
    stale_reasons,
)
from backend.application.llm_config_service import get_active_verified_config
from backend.domain.jd.enums import JDStatus
from backend.domain.jd.matching_v2 import (
    HARD_FILTER_POLICY_VERSION,
    MATCH_PROMPT_VERSION,
    MATCH_SCHEMA_VERSION,
    MATCHER_VERSION,
    MatchMode,
    MatchStatus,
    aggregate_dimensions,
    evaluate_hard_requirements,
    extract_hard_requirements_from_jd,
)
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    JDMatchResultModel,
    JobDescriptionModel,
    ResumeFactModel,
    ResumeModel,
)
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.matchers.llm_jd_matcher import EvidenceBoundJDMatcher, HeuristicJDMatcher, LLMJDMatcherError


class JDMatchingError(ValueError):
    def __init__(self, message: str, code: int = 1001) -> None:
        super().__init__(message)
        self.code = code


class DimensionMatcher(Protocol):
    last_usage: dict[str, Any]
    last_model: str | None

    async def score_dimensions(self, *, jd_summary: dict[str, Any], catalog: list[Any]) -> list[Any]: ...


@dataclass(frozen=True)
class MatchRunResult:
    id: uuid.UUID
    status: str
    mode: str
    input_fingerprint: str | None
    reused: bool = False


def serialize_match_v2(row: JDMatchResultModel, *, expected_fingerprint: str | None = None) -> dict[str, Any]:
    reasons = (
        stale_reasons(row, expected_fingerprint=expected_fingerprint)
        if expected_fingerprint
        else ([] if row.status == MatchStatus.READY.value else ["result_failed_or_incomplete"])
    )
    return {
        "id": str(row.id),
        "resume_id": str(row.resume_id),
        "jd_id": str(row.jd_id),
        "status": row.status,
        "mode": row.mode,
        "match_score": row.match_score,
        "recommendation": row.recommendation,
        "human_confirmation_required": any(item.get("human_confirmation_required") for item in row.hard_filters or []),
        "hard_filters": row.hard_filters,
        "dimension_scores": row.dimension_scores,
        "evidence": row.evidence,
        "coverage": row.coverage,
        "confidence": row.confidence,
        "risk": row.risk,
        "gap": row.gap,
        "detail": row.detail,
        "matcher_version": row.matcher_version,
        "hard_filter_policy_version": row.hard_filter_policy_version,
        "prompt_version": row.prompt_version,
        "schema_version": row.schema_version,
        "model": {"provider": row.provider, "name": row.model_name},
        "input_fingerprint": row.input_fingerprint,
        "stale": bool(reasons),
        "stale_reasons": reasons,
        "failure_code": row.failure_code,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


class HybridJDMatchingService:
    def __init__(self, matcher: DimensionMatcher | None = None) -> None:
        self._matcher = matcher

    async def create_match(
        self,
        session: AsyncSession,
        *,
        jd_id: uuid.UUID,
        resume_id: uuid.UUID,
        force: bool = False,
        dispatch: bool = True,
    ) -> MatchRunResult:
        jd, _resume, profile = await self._load_inputs(session, jd_id=jd_id, resume_id=resume_id)
        config = await get_active_verified_config(session)
        provider = getattr(config, "provider", None) if config is not None else None
        model_name = getattr(config, "model_name", None) if config is not None else None
        if config is None:
            raise JDMatchingError("LLM not configured or not verified", 428)
        fingerprint = current_match_fingerprint(jd=jd, profile=profile, provider=provider, model_name=model_name)
        if not force:
            ready = await self._find_existing(
                session,
                jd_id=jd_id,
                resume_id=resume_id,
                fingerprint=fingerprint,
                status=MatchStatus.READY.value,
            )
            if ready is not None:
                return MatchRunResult(ready.id, ready.status, ready.mode, ready.input_fingerprint, reused=True)
        active = await self._find_existing(
            session,
            jd_id=jd_id,
            resume_id=resume_id,
            fingerprint=fingerprint,
            status=None,
            active=True,
        )
        if active is not None:
            return MatchRunResult(active.id, active.status, active.mode, active.input_fingerprint, reused=True)
        run_id = uuid.uuid4()
        row_id = uuid.uuid4()
        row = JDMatchResultModel(
            id=row_id,
            jd_id=jd_id,
            resume_id=resume_id,
            match_score=None,
            recommendation="manual_review",
            status=MatchStatus.QUEUED.value,
            mode=MatchMode.HYBRID_V2.value,
            processing_run_id=run_id,
            input_fingerprint=fingerprint,
            matcher_version=MATCHER_VERSION,
            hard_filter_policy_version=HARD_FILTER_POLICY_VERSION,
            prompt_version=MATCH_PROMPT_VERSION,
            schema_version=MATCH_SCHEMA_VERSION,
            provider=provider,
            model_name=model_name,
        )
        session.add(row)
        await session.commit()
        if not dispatch:
            return MatchRunResult(row_id, MatchStatus.QUEUED.value, MatchMode.HYBRID_V2.value, fingerprint)
        try:
            from backend.tasks.jd_match_tasks import process_jd_match

            process_jd_match(str(row_id), str(run_id))
        except Exception:
            await self.mark_failed(session, match_id=row_id, run_id=run_id, failure_code="JD_MATCH_DISPATCH_FAILED")
            return MatchRunResult(row_id, MatchStatus.FAILED.value, MatchMode.HYBRID_V2.value, fingerprint)
        return MatchRunResult(row_id, MatchStatus.QUEUED.value, MatchMode.HYBRID_V2.value, fingerprint)

    async def run_match(self, session: AsyncSession, match_id: uuid.UUID, run_id: uuid.UUID) -> str:
        row = await session.get(JDMatchResultModel, match_id)
        if (
            row is None
            or row.processing_run_id != run_id
            or row.status not in {MatchStatus.QUEUED.value, MatchStatus.RUNNING.value}
        ):
            return "stale"
        await self._mark_running(session, match_id=match_id, run_id=run_id)
        jd, _resume, profile = await self._load_inputs(session, jd_id=row.jd_id, resume_id=row.resume_id)
        facts = await self._load_facts(session, row.resume_id)
        config = await get_active_verified_config(session)
        if config is None:
            raise JDMatchingError("LLM not configured or not verified", 428)
        provider = getattr(config, "provider", None)
        model_name = getattr(config, "model_name", None)
        expected = current_match_fingerprint(jd=jd, profile=profile, provider=provider, model_name=model_name)
        if row.input_fingerprint != expected:
            return "stale"
        catalog = build_match_source_catalog(jd, profile, facts)
        requirements = extract_hard_requirements_from_jd(jd)
        hard_filters = evaluate_hard_requirements(
            requirements,
            profile=_profile_dict(profile),
            facts=[_fact_dict(fact) for fact in facts],
        )
        matcher = self._matcher
        if matcher is None:
            try:
                matcher = (
                    EvidenceBoundJDMatcher(LLMGateway.from_config(config))
                    if config is not None
                    else HeuristicJDMatcher()
                )
            except Exception:
                matcher = HeuristicJDMatcher()
        await session.rollback()
        try:
            dimensions = await matcher.score_dimensions(
                jd_summary={
                    "title": jd.title,
                    "company": jd.company,
                    "seniority": jd.seniority,
                    "responsibilities": jd.responsibilities,
                    "required_skills": jd.required_skills,
                },
                catalog=catalog,
            )
        except (LLMJDMatcherError, ValueError) as exc:
            await self.mark_failed(session, match_id=match_id, run_id=run_id, failure_code="JD_MATCH_LLM_INVALID")
            raise JDMatchingError("JD match analysis failed", 5001) from exc
        result = aggregate_dimensions(hard_filters, dimensions)
        result.evidence = catalog
        values = {
            "status": MatchStatus.READY.value,
            "match_score": result.match_score,
            "recommendation": result.recommendation.value,
            "hard_filters": [item.model_dump(mode="json") for item in result.hard_filters],
            "dimension_scores": [item.model_dump(mode="json") for item in result.dimension_scores],
            "evidence": [item.model_dump(mode="json") for item in catalog],
            "coverage": result.coverage,
            "confidence": result.confidence,
            "detail": result.detail,
            "input_snapshot": fingerprint_parts(jd=jd, profile=profile, provider=provider, model_name=model_name),
            "model_name": matcher.last_model or model_name,
            "provider": provider,
            "failure_code": None,
            "completed_at": datetime.now(UTC),
        }
        updated = await self._write_owned(session, match_id=match_id, run_id=run_id, values=values)
        return MatchStatus.READY.value if updated else "stale"

    async def mark_failed(
        self, session: AsyncSession, *, match_id: uuid.UUID, run_id: uuid.UUID, failure_code: str
    ) -> None:
        await self._write_owned(
            session,
            match_id=match_id,
            run_id=run_id,
            values={
                "status": MatchStatus.FAILED.value,
                "failure_code": failure_code,
                "completed_at": datetime.now(UTC),
            },
        )

    async def get_detail(self, session: AsyncSession, match_id: uuid.UUID) -> dict[str, Any] | None:
        row = await session.get(JDMatchResultModel, match_id)
        if row is None:
            return None
        expected = None
        if row.mode == MatchMode.HYBRID_V2.value:
            profile = (
                await session.execute(
                    select(CandidateProfileModel).where(CandidateProfileModel.resume_id == row.resume_id)
                )
            ).scalar_one_or_none()
            jd = await session.get(JobDescriptionModel, row.jd_id)
            if jd is not None and profile is not None:
                expected = current_match_fingerprint(
                    jd=jd, profile=profile, provider=row.provider, model_name=row.model_name
                )
        return serialize_match_v2(row, expected_fingerprint=expected)

    async def list_for_jd(
        self,
        session: AsyncSession,
        *,
        jd_id: uuid.UUID,
        resume_id: uuid.UUID | None = None,
        status: str | None = None,
        mode: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        conditions = [JDMatchResultModel.jd_id == jd_id]
        if resume_id:
            conditions.append(JDMatchResultModel.resume_id == resume_id)
        if status:
            conditions.append(JDMatchResultModel.status == status)
        if mode:
            conditions.append(JDMatchResultModel.mode == mode)
        rows = (
            (
                await session.execute(
                    select(JDMatchResultModel)
                    .where(*conditions)
                    .order_by(JDMatchResultModel.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return {
            "items": [serialize_match_v2(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }

    async def _load_inputs(
        self,
        session: AsyncSession,
        *,
        jd_id: uuid.UUID,
        resume_id: uuid.UUID,
    ) -> tuple[JobDescriptionModel, ResumeModel, CandidateProfileModel]:
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDMatchingError("Job description not found", 1002)
        if jd.status != JDStatus.READY.value:
            raise JDMatchingError("Job description must be ready", 1003)
        resume = await session.get(ResumeModel, resume_id)
        if resume is None:
            raise JDMatchingError("Resume not found", 1002)
        if resume.status not in {"classified", "evaluated"}:
            raise JDMatchingError("Resume is not ready for matching", 1003)
        profile = (
            await session.execute(
                select(CandidateProfileModel)
                .where(CandidateProfileModel.resume_id == resume_id)
                .options(noload(CandidateProfileModel.resume))
            )
        ).scalar_one_or_none()
        if profile is None:
            raise JDMatchingError("Resume does not have a candidate profile", 1003)
        return jd, resume, profile

    async def _load_facts(self, session: AsyncSession, resume_id: uuid.UUID) -> list[ResumeFactModel]:
        return list(
            (await session.execute(select(ResumeFactModel).where(ResumeFactModel.resume_id == resume_id)))
            .scalars()
            .all()
        )

    async def _find_existing(
        self,
        session: AsyncSession,
        *,
        jd_id: uuid.UUID,
        resume_id: uuid.UUID,
        fingerprint: str,
        status: str | None,
        active: bool = False,
    ) -> JDMatchResultModel | None:
        conditions = [
            JDMatchResultModel.jd_id == jd_id,
            JDMatchResultModel.resume_id == resume_id,
            JDMatchResultModel.mode == MatchMode.HYBRID_V2.value,
            JDMatchResultModel.input_fingerprint == fingerprint,
        ]
        if active:
            conditions.append(JDMatchResultModel.status.in_([MatchStatus.QUEUED.value, MatchStatus.RUNNING.value]))
        elif status is not None:
            conditions.append(JDMatchResultModel.status == status)
        return (
            await session.execute(
                select(JDMatchResultModel)
                .where(*conditions)
                .order_by(JDMatchResultModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _mark_running(self, session: AsyncSession, *, match_id: uuid.UUID, run_id: uuid.UUID) -> bool:
        return await self._write_owned(
            session,
            match_id=match_id,
            run_id=run_id,
            values={"status": MatchStatus.RUNNING.value, "started_at": datetime.now(UTC)},
        )

    async def _write_owned(
        self,
        session: AsyncSession,
        *,
        match_id: uuid.UUID,
        run_id: uuid.UUID,
        values: dict[str, object],
    ) -> bool:
        result = await session.execute(
            update(JDMatchResultModel)
            .where(JDMatchResultModel.id == match_id, JDMatchResultModel.processing_run_id == run_id)
            .values(**values)
        )
        if getattr(result, "rowcount", 0) != 1:
            await session.rollback()
            return False
        await session.commit()
        return True


def _profile_dict(profile: CandidateProfileModel) -> dict[str, Any]:
    return {
        "education": profile.education,
        "work_experiences": profile.work_experiences,
        "projects": profile.projects,
        "skills": profile.skills,
        "certificates": profile.certificates,
        "ability_tags": profile.ability_tags,
        "interview_clues": profile.interview_clues,
        "risks": profile.risks,
    }


def _fact_dict(fact: ResumeFactModel) -> dict[str, Any]:
    return {
        "fact_type": fact.fact_type,
        "fact_key": fact.fact_key,
        "fact_value": fact.fact_value,
        "evidence_source_text": fact.evidence_source_text,
        "evidence_page": fact.evidence_page,
        "evidence_section": fact.evidence_section,
        "confidence": fact.confidence,
        "parser_version": fact.parser_version,
    }


__all__ = ["HybridJDMatchingService", "JDMatchingError", "MatchRunResult", "serialize_match_v2"]
