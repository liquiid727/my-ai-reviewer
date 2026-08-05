"""Match Assessment API (RIP-013 §9, §7.3).

Create is idempotent: it returns the reused completed assessment (200) or
persists a queued row and dispatches the worker after commit (202). Detail
returns the immutable completed result only — never provider raw output or
unmasked content.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application.match_assessment import (
    AssessmentInputNotReadyError,
    AssessmentNotFoundError,
    AssessmentUnsupportedPolicyError,
    AssessmentVersionNotFoundError,
    CreateAssessmentCommand,
    MatchAssessmentError,
    MatchAssessmentQueries,
    MatchAssessmentUseCases,
    assessment_payload,
    created_payload,
)
from backend.domain.match_assessment.lifecycle import (
    MatchActiveExistsError,
    MatchLifecycleError,
    MatchRetryNotAllowedError,
    MatchScopeMismatchError,
)
from backend.infrastructure.db.database import get_db

router = APIRouter(prefix="/match-assessments", tags=["match-assessments"])


class CreateAssessmentRequest(BaseModel):
    job_target_id: uuid.UUID | None = None
    jd_version_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    policy_version: str = "match-v1"
    force: bool = False


def _error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, MatchLifecycleError):
        if isinstance(exc, MatchScopeMismatchError):
            return HTTPException(status_code=422, detail=str(exc))
        if isinstance(exc, MatchActiveExistsError):
            return HTTPException(status_code=409, detail=str(exc))
        if isinstance(exc, MatchRetryNotAllowedError):
            return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, AssessmentInputNotReadyError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, AssessmentVersionNotFoundError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, AssessmentUnsupportedPolicyError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="match assessment error")


@router.post("")
async def create_match_assessment(
    request: CreateAssessmentRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        result = await MatchAssessmentUseCases().create(
            session,
            CreateAssessmentCommand(
                job_target_id=request.job_target_id,
                jd_version_id=request.jd_version_id,
                resume_version_id=request.resume_version_id,
                policy_version=request.policy_version,
                force=request.force,
            ),
        )
    except MatchLifecycleError as exc:
        raise _error_response(exc) from exc
    except MatchAssessmentError as exc:
        raise _error_response(exc) from exc
    return APIResponse(data=created_payload(result))


@router.get("")
async def list_match_assessments(
    job_target_id: uuid.UUID | None = None,
    jd_version_id: uuid.UUID | None = None,
    resume_version_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    before_created_at: datetime | None = None,
    before_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    rows, has_more = await MatchAssessmentQueries().list(
        session,
        job_target_id=job_target_id,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        status=status,
        limit=limit,
        before_created_at=before_created_at,
        before_id=before_id,
    )
    return APIResponse(
        data={
            "assessments": [assessment_payload(a) for a in rows],
            "next_before_created_at": (
                rows[-1].created_at.isoformat() if rows and rows[-1].created_at else None
            ),
            # a terminal page carries no cursor: the client must not page again
            "next_before_id": str(rows[-1].id) if rows and has_more else None,
        }
    )


@router.get("/{assessment_id}")
async def get_match_assessment(
    assessment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        row = await MatchAssessmentQueries().get(session, assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIResponse(data=assessment_payload(row))


@router.post("/{assessment_id}/retry")
async def retry_match_assessment(
    assessment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        result = await MatchAssessmentUseCases().retry(session, assessment_id)
    except MatchLifecycleError as exc:
        raise _error_response(exc) from exc
    except MatchAssessmentError as exc:
        raise _error_response(exc) from exc
    return APIResponse(data=created_payload(result))
