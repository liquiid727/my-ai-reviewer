"""JD library API, preserving the legacy synchronous JD/match contracts."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse, JDMatchRequest, JDMatchResultData, JobDescriptionData
from backend.application.jd_import_service import MAX_JD_FILE_SIZE, JDImportError, JDImportService
from backend.application.jd_service import commands as jd_commands
from backend.application.jd_service import queries as jd_queries
from backend.application.llm_config_service import has_verified_config
from backend.domain.jd.schemas import (
    JDPublishRequest,
    JDReextractRequest,
    JDReviewPatchRequest,
    JDStructuredPatch,
    JDTextImportRequest,
    JDURLImportRequest,
    JobDescriptionInput,
)
from backend.infrastructure.db.database import get_db

router = APIRouter(prefix="/jd", tags=["jd"])

LLM_NOT_READY_CODE = 428
LLM_NOT_READY_MESSAGE = "LLM not configured or not verified"


def _jd_payload(data: dict[str, Any]) -> dict[str, Any]:
    return JobDescriptionData(**data).model_dump(mode="json")


def _match_payload(data: dict[str, Any]) -> dict[str, Any]:
    return JDMatchResultData(**data).model_dump(mode="json")


def _import_result_response(result: Any) -> APIResponse:
    data = _jd_payload(jd_queries.serialize_jd(result.jd))
    if result.dispatch_failed:
        return APIResponse(code=5004, message="JD processing dispatch failed", data=data)
    return APIResponse(data=data)


async def _require_llm(session: AsyncSession) -> APIResponse | None:
    if not await has_verified_config(session):
        return APIResponse(code=LLM_NOT_READY_CODE, message=LLM_NOT_READY_MESSAGE)
    return None


def _get_extractor():
    """Test seam for legacy POST /jd auto-extraction."""
    return jd_commands._get_legacy_extractor()


@router.post("/import/text", response_model=APIResponse)
async def import_jd_text(
    payload: JDTextImportRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    try:
        result = await JDImportService().import_text(
            session,
            raw_text=payload.raw_text,
            title=payload.title,
            company=payload.company,
            allow_duplicate=payload.allow_duplicate,
        )
    except JDImportError as exc:
        return APIResponse(code=exc.code, message=str(exc))
    return _import_result_response(result)


@router.post("/import/file", response_model=APIResponse)
async def import_jd_file(
    file: UploadFile = File(...),
    allow_duplicate: bool = Query(False),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    try:
        result = await JDImportService().import_file(
            session,
            filename=file.filename or "job-description",
            content_type=file.content_type,
            data=await file.read(MAX_JD_FILE_SIZE + 1),
            allow_duplicate=allow_duplicate,
        )
    except JDImportError as exc:
        return APIResponse(code=exc.code, message=str(exc))
    return _import_result_response(result)


@router.post("/import/url", response_model=APIResponse)
async def import_jd_url(
    payload: JDURLImportRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    try:
        result = await JDImportService().import_url(
            session,
            url=str(payload.url),
            allow_duplicate=payload.allow_duplicate,
        )
    except JDImportError as exc:
        return APIResponse(code=exc.code, message=str(exc))
    return _import_result_response(result)


@router.get("/resume/{resume_id}/matches", response_model=APIResponse)
async def list_jd_matches(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    rows = await jd_queries.list_matches_for_resume(session, resume_id)
    if rows is None:
        return APIResponse(code=404, message="Resume not found")
    return APIResponse(data=[_match_payload(row) for row in rows])


@router.post("/match", response_model=APIResponse)
async def match_resume_to_jd(
    payload: JDMatchRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    try:
        result = await jd_commands.match_resume(
            session,
            resume_id=uuid.UUID(payload.resume_id),
            jd_id=uuid.UUID(payload.jd_id) if payload.jd_id else None,
            jd_input=payload.jd,
        )
    except jd_commands.JDCommandError as exc:
        return APIResponse(code=exc.code, message=exc.message)
    return APIResponse(data=_match_payload(result.payload))


@router.post("", response_model=APIResponse)
async def create_job_description(
    payload: JobDescriptionInput,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Legacy synchronous create endpoint retained for existing matching callers."""
    try:
        result = await jd_commands.create_legacy_job_description(
            session,
            payload,
            extractor=_get_extractor,
        )
    except jd_commands.JDCommandError as exc:
        if exc.code == 502:
            from fastapi import HTTPException

            raise HTTPException(status_code=502, detail="JD_EXTRACTION_FAILED") from exc
        return APIResponse(code=exc.code, message=exc.message)
    return APIResponse(data=_jd_payload(result.payload))


@router.get("", response_model=APIResponse)
async def list_job_descriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    source_type: Literal["text", "file", "url"] | None = None,
    status: Literal["processing", "duplicate_pending", "needs_review", "ready", "failed", "archived"] | None = None,
    direction: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    data = await jd_queries.list_job_descriptions(
        session,
        page=page,
        page_size=page_size,
        q=q,
        source_type=source_type,
        status=status,
        direction=direction,
    )
    return APIResponse(data=data)


@router.get("/match/{match_id}", response_model=APIResponse)
async def get_jd_match(match_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    payload = await jd_queries.get_match_payload(session, match_id)
    if payload is None:
        return APIResponse(code=404, message="JD match result not found")
    return APIResponse(data=_match_payload(payload))


@router.get("/{jd_id}", response_model=APIResponse)
async def get_job_description(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    payload = await jd_queries.get_jd_payload(session, jd_id)
    if payload is None:
        return APIResponse(code=404, message="Job description not found")
    return APIResponse(data=_jd_payload(payload))


@router.patch("/{jd_id}", response_model=APIResponse)
async def patch_job_description(
    jd_id: uuid.UUID,
    payload: JDStructuredPatch,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    changed_fields = set(payload.model_fields_set) - {"expected_updated_at"}
    field_values = {field: getattr(payload, field) for field in changed_fields}
    try:
        data = await jd_commands.patch_job_description(
            session,
            jd_id,
            changed_fields=changed_fields,
            field_values=field_values,
            expected_updated_at=payload.expected_updated_at,
        )
    except jd_commands.JDCommandError as exc:
        return APIResponse(code=exc.code, message=exc.message)
    return APIResponse(data=_jd_payload(data))


@router.post("/{jd_id}/retry", response_model=APIResponse)
async def retry_jd(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    try:
        result = await jd_commands.retry_jd(session, jd_id)
    except jd_commands.JDCommandError as exc:
        return APIResponse(code=exc.code, message=exc.message)
    return _import_result_response(result)


@router.post("/{jd_id}/reextract", response_model=APIResponse)
async def reextract_jd(
    jd_id: uuid.UUID,
    payload: JDReextractRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    try:
        result = await jd_commands.reextract_jd(
            session,
            jd_id,
            overwrite_manual=payload.overwrite_manual,
        )
    except jd_commands.JDCommandError as exc:
        return APIResponse(code=exc.code, message=exc.message)
    return _import_result_response(result)


@router.post("/{jd_id}/duplicate/confirm", response_model=APIResponse)
async def confirm_jd_duplicate(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    try:
        result = await jd_commands.confirm_duplicate(session, jd_id)
    except jd_commands.JDCommandError as exc:
        return APIResponse(code=exc.code, message=exc.message)
    return _import_result_response(result)


@router.post("/{jd_id}/duplicate/cancel", response_model=APIResponse)
async def cancel_jd_duplicate(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    try:
        await jd_commands.cancel_duplicate(session, jd_id)
    except jd_commands.JDCommandError as exc:
        return APIResponse(code=exc.code, message=exc.message)
    return APIResponse(message="Duplicate job description cancelled")


@router.patch("/{jd_id}/review", response_model=APIResponse)
async def patch_jd_review(
    jd_id: uuid.UUID,
    payload: JDReviewPatchRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    from backend.application.jd_review_draft import (
        JDReviewConflictError,
        JDReviewDraftUseCases,
        JDReviewNotInReviewError,
    )

    try:
        result = await JDReviewDraftUseCases().save_review_draft(
            session,
            jd_id,
            expected_review_revision=payload.expected_review_revision,
            draft=payload.draft,
        )
    except JDReviewConflictError as exc:
        return APIResponse(code=409, message=str(exc))
    except JDReviewNotInReviewError as exc:
        return APIResponse(code=409, message=str(exc))
    return APIResponse(data=result)


@router.post("/{jd_id}/publish", response_model=APIResponse)
async def publish_jd_version(
    jd_id: uuid.UUID,
    payload: JDPublishRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    from backend.application.jd_publish import (
        JDPublishConflictError,
        JDPublishInvalidError,
        JDPublishUseCases,
        PublishJDCommand,
    )

    try:
        version = await JDPublishUseCases().publish(
            session,
            PublishJDCommand(
                jd_id=jd_id,
                expected_review_revision=payload.expected_review_revision,
                publication_reason=payload.publication_reason,
            ),
        )
    except JDPublishConflictError as exc:
        return APIResponse(code=409, message=str(exc))
    except JDPublishInvalidError as exc:
        return APIResponse(code=422, message=str(exc))
    return APIResponse(
        data={
            "id": str(version.id),
            "version_no": version.version_no,
            "content_hash": version.content_hash,
            "schema_version": version.schema_version,
            "publication_reason": version.publication_reason,
            "published_at": version.published_at.isoformat() if version.published_at else None,
        }
    )


@router.post("/{jd_id}/reparse", response_model=APIResponse)
async def reparse_jd(
    jd_id: uuid.UUID,
    payload: JDReextractRequest | None = None,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    from backend.application.jd_lifecycle import JDLifecycleError, JDLifecycleUseCases

    overwrite_manual = bool(payload.overwrite_manual) if payload else False
    try:
        run_id = await JDLifecycleUseCases().start_reparse(session, jd_id, overwrite_manual=overwrite_manual)
    except JDLifecycleError as exc:
        return APIResponse(code=409, message=str(exc))
    return APIResponse(data={"run_id": str(run_id), "status": "processing"})


@router.post("/{jd_id}/draft/abandon", response_model=APIResponse)
async def abandon_jd_draft(
    jd_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    from backend.application.jd_lifecycle import JDLifecycleError, JDLifecycleUseCases

    try:
        await JDLifecycleUseCases().abandon_draft(session, jd_id)
    except JDLifecycleError as exc:
        return APIResponse(code=409, message=str(exc))
    return APIResponse(message="Draft abandoned")


@router.post("/{jd_id}/archive", response_model=APIResponse)
async def archive_jd(
    jd_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    from backend.application.jd_lifecycle import JDLifecycleError, JDLifecycleUseCases

    try:
        await JDLifecycleUseCases().archive(session, jd_id)
    except JDLifecycleError as exc:
        return APIResponse(code=409, message=str(exc))
    return APIResponse(message="Job description archived")


@router.delete("/{jd_id}", response_model=APIResponse)
async def delete_job_description(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    try:
        await jd_commands.delete_job_description(session, jd_id)
    except jd_commands.JDCommandError as exc:
        return APIResponse(code=exc.code, message=exc.message)
    return APIResponse(message="Job description deleted")
