"""Resume read-side use cases (status/detail/facts/profile/evaluation)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.application.resume_service.diagnostics import (
    normalize_failure_details,
    public_error_message,
)
from backend.application.resume_service.pipeline import get_privacy_manifest
from backend.application.resume_service.runs import get_latest_run, reconcile_stale_resume
from backend.domain.resume.enums import ResumeStatus, resume_status_value
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    ResumeEvaluationModel,
    ResumeFactModel,
    ResumeModel,
)

PIPELINE_STEPS = ["text_extract", "privacy_scan", "llm_parse", "classify", "evaluate"]

STATUS_TO_STEP_INDEX: dict[str, int] = {
    ResumeStatus.UPLOADED.value: -1,
    ResumeStatus.PRIVACY_SCANNING.value: 0,
    ResumeStatus.PRIVACY_REVIEW_REQUIRED.value: 1,
    ResumeStatus.TEXT_MASKED.value: 1,
    ResumeStatus.LLM_PARSING.value: 1,
    ResumeStatus.FACT_EXTRACTED.value: 2,
    ResumeStatus.CLASSIFIED.value: 3,
    ResumeStatus.EVALUATING.value: 3,
    ResumeStatus.EVALUATED.value: 4,
}


async def get_resume(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel | None:
    return await session.get(ResumeModel, resume_id)


async def get_resume_with_evaluations(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumeModel | None:
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id).options(selectinload(ResumeModel.evaluations))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def completed_steps(status: str) -> list[str]:
    idx = STATUS_TO_STEP_INDEX.get(status, -1)
    return PIPELINE_STEPS[: idx + 1]


def completed_steps_from_data(
    *,
    masked_text: str | None,
    parsed_result: dict[str, Any] | None,
    has_evaluations: bool,
) -> list[str]:
    steps: list[str] = []
    if masked_text:
        steps.append("text_extract")
    if parsed_result:
        steps.append("llm_parse")
        if "classification" in parsed_result:
            steps.append("classify")
    if has_evaluations:
        steps.append("evaluate")
    return steps


def current_step(status: str) -> str:
    if status == ResumeStatus.FAILED.value:
        return "failed"
    idx = STATUS_TO_STEP_INDEX.get(status, -1)
    if idx + 1 < len(PIPELINE_STEPS):
        return PIPELINE_STEPS[idx + 1]
    return "done"


async def build_status_payload(session: AsyncSession, resume_id: uuid.UUID) -> dict[str, Any] | None:
    if hasattr(session, "execute"):
        await reconcile_stale_resume(session, resume_id)
    resume = await get_resume_with_evaluations(session, resume_id)
    if resume is None:
        return None
    run = await get_latest_run(session, resume_id) if hasattr(session, "execute") else None
    status = resume_status_value(resume.status)
    if status == ResumeStatus.FAILED.value:
        completed = completed_steps_from_data(
            masked_text=resume.masked_text,
            parsed_result=resume.parsed_result,
            has_evaluations=bool(resume.evaluations),
        )
    else:
        completed = completed_steps(status)
    run_current_step = getattr(run, "current_step", None)
    run_details = normalize_failure_details(
        {
            "error_code": getattr(run, "error_code", None),
            "retryable": getattr(run, "retryable", False),
            "step": run_current_step,
            "attempt": getattr(run, "attempt", None),
        }
        if run is not None and getattr(run, "error_code", None)
        else None,
    )
    details = (
        normalize_failure_details(
            getattr(resume, "processing_error_details", None),
            getattr(resume, "parse_error", None),
        )
        or run_details
    )
    diagnostic = None
    if status == ResumeStatus.FAILED.value and details is not None:
        diagnostic = {
            "error_code": details["error_code"],
            "step": details.get("step"),
            "attempt": details.get("attempt"),
            "retryable": bool(details.get("retryable", False)),
        }
    return {
        "status": status,
        "current_step": ("failed" if status == ResumeStatus.FAILED.value else run_current_step or current_step(status)),
        "completed_steps": completed,
        "error": (
            details.get("public_message", public_error_message("RESUME_PROCESSING_FAILED"))
            if status == ResumeStatus.FAILED.value and details is not None
            else None
        ),
        "run_id": (
            str(getattr(resume, "processing_run_id", None))
            if getattr(resume, "processing_run_id", None) is not None
            else (str(run.id) if run is not None else None)
        ),
        "error_code": details.get("error_code") if details is not None else None,
        "retryable": bool(details.get("retryable", False)) if details is not None else False,
        "last_progress_at": getattr(run, "last_progress_at", None),
        "deadline_at": getattr(run, "deadline_at", None),
        "diagnostic": diagnostic,
    }


async def build_detail_payload(session: AsyncSession, resume_id: uuid.UUID) -> dict[str, Any] | None:
    resume = await get_resume(session, resume_id)
    if resume is None:
        return None
    manifest = await get_privacy_manifest(session, resume_id)
    privacy = (
        None
        if manifest is None
        else {
            "status": manifest.status,
            "revision": manifest.revision,
            "placeholders": manifest.placeholders,
            "risk_flags": manifest.risk_flags,
        }
    )
    return {
        "resume_id": str(resume.id),
        "status": resume.status,
        "masked_text": resume.masked_text,
        "parsed_result": resume.parsed_result,
        "privacy": privacy,
        "created_at": resume.created_at,
        "updated_at": resume.updated_at,
    }


async def list_fact_payloads(session: AsyncSession, resume_id: uuid.UUID) -> list[dict[str, Any]] | None:
    resume = await get_resume(session, resume_id)
    if resume is None:
        return None
    stmt = select(ResumeFactModel).where(ResumeFactModel.resume_id == resume_id)
    result = await session.execute(stmt)
    facts = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "fact_type": row.fact_type,
            "fact_key": row.fact_key,
            "fact_value": row.fact_value,
            "evidence_source_text": row.evidence_source_text,
            "evidence_page": row.evidence_page,
            "evidence_section": row.evidence_section,
            "confidence": row.confidence,
            "metadata": row.meta,
            "parser_version": row.parser_version,
            "created_at": row.created_at,
        }
        for row in facts
    ]


async def get_profile_payload(session: AsyncSession, resume_id: uuid.UUID) -> dict[str, Any] | None:
    resume = await get_resume(session, resume_id)
    if resume is None:
        return None
    stmt = select(CandidateProfileModel).where(CandidateProfileModel.resume_id == resume_id)
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        return {"_missing_profile": True}
    return {
        "id": str(profile.id),
        "resume_id": str(profile.resume_id),
        "identity": profile.identity,
        "education": profile.education,
        "work_experiences": profile.work_experiences,
        "projects": profile.projects,
        "skills": profile.skills,
        "certificates": profile.certificates,
        "ability_tags": profile.ability_tags,
        "interview_clues": profile.interview_clues,
        "risks": profile.risks,
        "parser_version": profile.parser_version,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


async def get_evaluation_payload(session: AsyncSession, resume_id: uuid.UUID) -> dict[str, Any] | None:
    resume = await get_resume_with_evaluations(session, resume_id)
    if resume is None:
        return None
    if not resume.evaluations:
        return {"_missing_evaluation": True}
    eval_record: ResumeEvaluationModel = resume.evaluations[-1]
    return {
        "evaluation_id": str(eval_record.id),
        "resume_id": str(eval_record.resume_id),
        "overall_score": eval_record.overall_score,
        "dimension_scores": eval_record.dimension_scores,
        "strengths": eval_record.strengths,
        "risks": eval_record.risks,
        "interview_suggestions": eval_record.interview_suggestions,
        "summary": eval_record.summary,
        "llm_model": eval_record.llm_model,
        "created_at": eval_record.created_at,
    }


async def get_resume_for_mutation(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumeModel | None:
    """Load a resume row for retry/reparse precondition checks."""
    return await get_resume(session, resume_id)
