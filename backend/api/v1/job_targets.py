"""Job Target API (RIP-010 §9.1, §9.3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application.job_target import (
    ArchiveTargetCommand,
    EnsureTargetCommand,
    JobDescriptionNotFoundError,
    JobTargetArchivedError,
    JobTargetNotFoundError,
    JobTargetRevisionConflictError,
    JobTargetUseCaseError,
    JobTargetUseCases,
    TargetResult,
    UpdateDefaultsCommand,
    VersionScopeMismatchError,
)
from backend.application.match_assessment import (
    MatchAssessmentQueries,
    MatchReportQueries,
    assessment_payload,
)
from backend.infrastructure.db.database import get_db

router = APIRouter(prefix="/job-targets", tags=["job-targets"])


class EnsureTargetRequest(BaseModel):
    jd_id: uuid.UUID
    default_jd_version_id: uuid.UUID | None = None
    default_resume_version_id: uuid.UUID | None = None


class UpdateDefaultsRequest(BaseModel):
    expected_revision: int
    default_jd_version_id: uuid.UUID | None = None
    default_resume_version_id: uuid.UUID | None = None


class ArchiveTargetRequest(BaseModel):
    expected_revision: int


def _target_payload(target: TargetResult) -> dict[str, object]:
    return {
        "id": str(target.id),
        "job_description_id": str(target.job_description_id),
        "default_jd_version_id": (
            str(target.default_jd_version_id) if target.default_jd_version_id else None
        ),
        "default_resume_version_id": (
            str(target.default_resume_version_id) if target.default_resume_version_id else None
        ),
        "revision": target.revision,
        "created_at": target.created_at.isoformat() if target.created_at else None,
        "updated_at": target.updated_at.isoformat() if target.updated_at else None,
        "archived_at": target.archived_at.isoformat() if target.archived_at else None,
        "created": target.created,
    }


def _error_response(exc: JobTargetUseCaseError) -> HTTPException:
    if isinstance(exc, JobTargetNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, JobDescriptionNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, JobTargetArchivedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, JobTargetRevisionConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, VersionScopeMismatchError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="job target error")


@router.post("")
async def ensure_job_target(
    request: EnsureTargetRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        result = await JobTargetUseCases().ensure(
            session,
            EnsureTargetCommand(
                jd_id=request.jd_id,
                default_jd_version_id=request.default_jd_version_id,
                default_resume_version_id=request.default_resume_version_id,
            ),
        )
    except JobTargetUseCaseError as exc:
        raise _error_response(exc) from exc
    return APIResponse(data=_target_payload(result))


@router.get("")
async def list_job_targets(
    include_archived: bool = False,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    targets = await JobTargetUseCases().list_active(
        session, include_archived=include_archived
    )
    return APIResponse(data={"targets": [_target_payload(t) for t in targets]})


@router.get("/{target_id}")
async def get_job_target(
    target_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        target = await JobTargetUseCases().get(session, target_id)
    except JobTargetUseCaseError as exc:
        raise _error_response(exc) from exc
    return APIResponse(data=_target_payload(target))


@router.patch("/{target_id}")
async def update_job_target_defaults(
    target_id: uuid.UUID,
    request: UpdateDefaultsRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        result = await JobTargetUseCases().update_defaults(
            session,
            UpdateDefaultsCommand(
                target_id=target_id,
                expected_revision=request.expected_revision,
                default_jd_version_id=request.default_jd_version_id,
                default_resume_version_id=request.default_resume_version_id,
            ),
        )
    except JobTargetUseCaseError as exc:
        raise _error_response(exc) from exc
    return APIResponse(data=_target_payload(result))


@router.get("/{target_id}/match-assessments")
async def list_target_match_assessments(
    target_id: uuid.UUID,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    before_created_at: datetime | None = None,
    before_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        await JobTargetUseCases().get(session, target_id)
    except JobTargetUseCaseError as exc:
        raise _error_response(exc) from exc
    rows, has_more = await MatchAssessmentQueries().list(
        session,
        job_target_id=target_id,
        status=status,
        limit=limit,
        before_created_at=before_created_at,
        before_id=before_id,
    )
    items: list[dict[str, object]] = []
    for row in rows:
        item: dict[str, object] = assessment_payload(row)
        if row.status == "completed":
            report = await MatchReportQueries().report(session, row.id)
            if report is not None:
                item["report"] = report
        items.append(item)
    return APIResponse(
        data={
            "assessments": items,
            "next_before_created_at": (
                rows[-1].created_at.isoformat() if rows and rows[-1].created_at else None
            ),
            # a terminal page carries no cursor: the client must not page again
            "next_before_id": str(rows[-1].id) if rows and has_more else None,
        }
    )


@router.post("/{target_id}/archive")
async def archive_job_target(
    target_id: uuid.UUID,
    request: ArchiveTargetRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        result = await JobTargetUseCases().archive(
            session,
            ArchiveTargetCommand(target_id=target_id, expected_revision=request.expected_revision),
        )
    except JobTargetUseCaseError as exc:
        raise _error_response(exc) from exc
    return APIResponse(data=_target_payload(result))
