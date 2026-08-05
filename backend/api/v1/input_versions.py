"""Input version API (RIP-010 §9): resume version publish/query and JD version query."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application.input_versions import (
    InputVersionError,
    JDVersionQueries,
    PrivacyRejectedError,
    PublishResumeVersionCommand,
    ResumeVersionResult,
    ResumeVersionUseCases,
    SourceNotReadyError,
    SourceRevisionChangedError,
    VersionNotFoundError,
)
from backend.infrastructure.db.database import get_db

router = APIRouter(tags=["input-versions"])


class PublishResumeVersionRequest(BaseModel):
    source_type: str
    resume_id: uuid.UUID | None = None
    draft_id: uuid.UUID | None = None
    source_revision: int | None = Field(default=None, ge=1)


def _resume_version_payload(result: ResumeVersionResult) -> dict[str, object]:
    return {
        "id": str(result.id),
        "source_type": result.source_type,
        "resume_id": str(result.resume_id) if result.resume_id else None,
        "draft_id": str(result.draft_id) if result.draft_id else None,
        "source_revision": result.source_revision,
        "content_hash": result.content_hash,
        "schema_version": result.schema_version,
        "privacy_policy_version": result.privacy_policy_version,
        "published_at": result.published_at.isoformat() if result.published_at else None,
        "created": result.created,
    }


def _jd_version_summary(version: Any) -> dict[str, object]:
    return {
        "id": str(version.id),
        "version_no": version.version_no,
        "content_hash": version.content_hash,
        "schema_version": version.schema_version,
        "parser_version": version.parser_version,
        "publication_reason": version.publication_reason,
        "published_at": version.published_at.isoformat() if version.published_at else None,
    }


def _jd_version_detail(version: Any) -> dict[str, object]:
    return {
        **_jd_version_summary(version),
        "normalized_text": version.normalized_text,
        "structured": version.structured,
        "evidence": version.evidence,
        "source_metadata": version.source_metadata,
    }


def _error_response(exc: InputVersionError) -> HTTPException:
    if isinstance(exc, SourceNotReadyError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, SourceRevisionChangedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, PrivacyRejectedError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, VersionNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="input version error")


@router.post("/resume-versions")
async def publish_resume_version(
    request: PublishResumeVersionRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    command = PublishResumeVersionCommand(
        source_type=request.source_type,
        resume_id=request.resume_id,
        draft_id=request.draft_id,
        source_revision=request.source_revision,
    )
    try:
        result = await ResumeVersionUseCases().publish_or_resolve(session, command)
    except InputVersionError as exc:
        raise _error_response(exc) from exc
    return APIResponse(data=_resume_version_payload(result))


@router.get("/resume-versions")
async def list_resume_versions(
    resume_id: uuid.UUID | None = Query(default=None),
    draft_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    from backend.application.input_versions import ResumeVersionQueries

    versions = await ResumeVersionQueries().list(
        session, resume_id=resume_id, draft_id=draft_id, limit=limit
    )
    return APIResponse(
        data={
            "versions": [
                {
                    "id": str(v.id),
                    "source_type": v.source_type,
                    "source_revision": v.source_revision,
                    "content_hash": v.content_hash,
                    "schema_version": v.schema_version,
                    "published_at": v.published_at.isoformat() if v.published_at else None,
                }
                for v in versions
            ]
        }
    )


@router.get("/resume-versions/{version_id}")
async def get_resume_version(
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    from backend.application.input_versions import ResumeVersionQueries

    version = await ResumeVersionQueries().get(session, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="resume version not found")
    return APIResponse(
        data={
            "id": str(version.id),
            "source_type": version.source_type,
            "resume_id": str(version.resume_id) if version.resume_id else None,
            "draft_id": str(version.draft_id) if version.draft_id else None,
            "source_revision": version.source_revision,
            "content_hash": version.content_hash,
            "masked_snapshot": version.masked_snapshot,
            "profile_snapshot": version.profile_snapshot,
            "evidence_catalog": version.evidence_catalog,
            "schema_version": version.schema_version,
            "privacy_policy_version": version.privacy_policy_version,
            "published_at": version.published_at.isoformat() if version.published_at else None,
        }
    )


@router.get("/jd/{jd_id}/versions")
async def list_jd_versions(
    jd_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    versions = await JDVersionQueries().list_for_jd(session, jd_id, limit=limit)
    return APIResponse(data={"versions": [_jd_version_summary(v) for v in versions]})


@router.get("/jd/{jd_id}/versions/{version_id}")
async def get_jd_version(
    jd_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    version = await JDVersionQueries().get(session, version_id)
    if version is None or version.job_description_id != jd_id:
        raise HTTPException(status_code=404, detail="JD version not found")
    return APIResponse(data=_jd_version_detail(version))
