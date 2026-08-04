"""JD library API, preserving the legacy synchronous JD/match contracts."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import asc, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse, JDMatchRequest, JDMatchResultData, JobDescriptionData
from backend.application.jd_import_service import MAX_JD_FILE_SIZE, JDImportError, JDImportService
from backend.application.llm_config_service import has_verified_config
from backend.config import get_settings
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.domain.jd.matching import JDMatchingService
from backend.domain.jd.schemas import (
    JDReextractRequest,
    JDStructuredPatch,
    JDTextImportRequest,
    JDURLImportRequest,
    JobDescriptionInput,
)
from backend.infrastructure.db.database import get_db
from backend.infrastructure.db.models import FileModel, JDMatchResultModel, JobDescriptionModel, ResumeModel
from backend.infrastructure.extractors.jd_extractor import JDExtractionError, JDExtractor
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.storage.minio_client import delete_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jd", tags=["jd"])

LLM_NOT_READY_CODE = 428
LLM_NOT_READY_MESSAGE = "LLM not configured or not verified"
_LIST_FIELDS = {"responsibilities", "required_skills", "preferred_skills"}


def _get_extractor() -> JDExtractor:
    """Build the legacy extractor from settings; old POST /jd remains compatible."""
    return JDExtractor(gateway=LLMGateway.from_settings())


def _jd_to_dict(jd: JobDescriptionModel, *, include_raw_text: bool = True) -> dict[str, Any]:
    data = JobDescriptionData(
        id=str(jd.id),
        title=jd.title,
        company=jd.company,
        raw_text=jd.raw_text if include_raw_text else "",
        required_skills=jd.required_skills,
        responsibilities=jd.responsibilities,
        seniority=jd.seniority,
        extraction_source=jd.extraction_source,
        source_type=jd.source_type,
        source_url=jd.source_url,
        source_file_id=str(jd.source_file_id) if jd.source_file_id else None,
        location=jd.location,
        preferred_skills=jd.preferred_skills,
        status=jd.status,
        processing_step=jd.processing_step,
        processing_error=jd.processing_error,
        duplicate_of_id=str(jd.duplicate_of_id) if jd.duplicate_of_id else None,
        field_sources=jd.field_sources,
        parser_version=jd.parser_version,
        updated_at=jd.updated_at,
        created_at=jd.created_at,
    )
    return data.model_dump(mode="json")


def _import_result_response(result: Any) -> APIResponse:
    data = _jd_to_dict(result.jd)
    if result.dispatch_failed:
        return APIResponse(code=5004, message="JD processing dispatch failed", data=data)
    return APIResponse(data=data)


async def _require_llm(session: AsyncSession) -> APIResponse | None:
    if not await has_verified_config(session):
        return APIResponse(code=LLM_NOT_READY_CODE, message=LLM_NOT_READY_MESSAGE)
    return None


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
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")
    result = await session.execute(
        select(JDMatchResultModel)
        .where(JDMatchResultModel.resume_id == resume_id)
        .order_by(JDMatchResultModel.created_at.desc())
    )
    return APIResponse(data=[_match_row_to_dict(row) for row in result.scalars().all()])


@router.post("/match", response_model=APIResponse)
async def match_resume_to_jd(
    payload: JDMatchRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    resume_id = uuid.UUID(payload.resume_id)
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    if payload.jd_id:
        jd = await session.get(JobDescriptionModel, uuid.UUID(payload.jd_id))
        if jd is None:
            return APIResponse(code=404, message="Job description not found")
        if jd.status != JDStatus.READY.value:
            return APIResponse(code=1003, message="Job description is not ready")
    elif payload.jd:
        required_skills = [
            {"name": name, "critical": name in (payload.jd.critical_skills or [])}
            for name in payload.jd.required_skills
        ]
        jd = JobDescriptionModel(
            title=payload.jd.title,
            company=payload.jd.company,
            raw_text=payload.jd.raw_text,
            required_skills=required_skills,
        )
        session.add(jd)
        await session.flush()
    else:
        return APIResponse(code=400, message="Either jd_id or jd must be provided")

    record = await JDMatchingService().match(session, resume_id, jd)
    await session.commit()
    return APIResponse(data=_match_row_to_dict(record))


@router.post("", response_model=APIResponse)
async def create_job_description(
    payload: JobDescriptionInput,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Legacy synchronous create endpoint retained for existing matching callers."""
    responsibilities: list[str] = []
    seniority: str | None = None
    extraction_source = "manual"
    skills_explicit = "required_skills" in payload.model_fields_set

    if payload.required_skills:
        required_skills = [
            {"name": name, "critical": name in (payload.critical_skills or [])}
            for name in payload.required_skills
        ]
    elif not skills_explicit and payload.raw_text.strip():
        try:
            extraction = await _get_extractor().extract(payload.raw_text)
        except JDExtractionError as exc:
            from fastapi import HTTPException

            raise HTTPException(status_code=502, detail="JD_EXTRACTION_FAILED") from exc
        required_skills = [skill.model_dump() for skill in extraction.required_skills]
        responsibilities = extraction.responsibilities
        seniority = extraction.seniority
        extraction_source = "llm"
    else:
        required_skills = []

    jd = JobDescriptionModel(
        title=payload.title,
        company=payload.company,
        raw_text=payload.raw_text,
        required_skills=required_skills,
        responsibilities=responsibilities,
        seniority=seniority,
        extraction_source=extraction_source,
        source_type="text",
        status=JDStatus.READY.value,
        processing_step=JDProcessingStep.DONE.value,
        field_sources={
            "required_skills": extraction_source,
            "responsibilities": extraction_source,
            "seniority": extraction_source,
        },
    )
    session.add(jd)
    await session.flush()
    await session.commit()
    return APIResponse(data=_jd_to_dict(jd))


@router.get("", response_model=APIResponse)
async def list_job_descriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    source_type: Literal["text", "file", "url"] | None = None,
    status: Literal["processing", "duplicate_pending", "ready", "failed"] | None = None,
    direction: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    conditions: list[Any] = []
    if q and q.strip():
        search = f"%{q.strip()}%"
        conditions.append(or_(JobDescriptionModel.title.ilike(search), JobDescriptionModel.company.ilike(search)))
    if source_type:
        conditions.append(JobDescriptionModel.source_type == source_type)
    if status:
        conditions.append(JobDescriptionModel.status == status)
    order = asc(JobDescriptionModel.updated_at) if direction == "asc" else desc(JobDescriptionModel.updated_at)
    result = await session.execute(
        select(
            JobDescriptionModel.id,
            JobDescriptionModel.title,
            JobDescriptionModel.company,
            JobDescriptionModel.location,
            JobDescriptionModel.source_type,
            JobDescriptionModel.status,
            JobDescriptionModel.processing_step,
            JobDescriptionModel.processing_error,
            JobDescriptionModel.seniority,
            JobDescriptionModel.updated_at,
            JobDescriptionModel.created_at,
        )
        .where(*conditions)
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total_statement = select(func.count()).select_from(JobDescriptionModel).where(*conditions)
    total = (await session.execute(total_statement)).scalar_one()
    items = [
        {
            "id": str(row.id),
            "title": row.title,
            "company": row.company,
            "location": row.location,
            "source_type": row.source_type,
            "status": row.status,
            "processing_step": row.processing_step,
            "processing_error": row.processing_error,
            "seniority": row.seniority,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.all()
    ]
    return APIResponse(data={"items": items, "page": page, "page_size": page_size, "total": total})


@router.get("/match/{match_id}", response_model=APIResponse)
async def get_jd_match(match_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    record = await session.get(JDMatchResultModel, match_id)
    if record is None:
        return APIResponse(code=404, message="JD match result not found")
    return APIResponse(data=_match_row_to_dict(record))


@router.get("/{jd_id}", response_model=APIResponse)
async def get_job_description(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=404, message="Job description not found")
    return APIResponse(data=_jd_to_dict(jd))


@router.patch("/{jd_id}", response_model=APIResponse)
async def patch_job_description(
    jd_id: uuid.UUID,
    payload: JDStructuredPatch,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=1002, message="Job description not found")
    changed_fields = set(payload.model_fields_set) - {"expected_updated_at"}
    if not changed_fields:
        return APIResponse(data=_jd_to_dict(jd))

    fields = dict(jd.field_sources or {})
    values: dict[str, Any] = {}
    for field in changed_fields:
        value = getattr(payload, field)
        if field in _LIST_FIELDS:
            values[field] = (
                []
                if value is None
                else [item.model_dump() if hasattr(item, "model_dump") else item for item in value]
            )
        else:
            values[field] = value
        fields[field] = "manual"
    values["field_sources"] = fields

    statement = (
        update(JobDescriptionModel)
        .where(JobDescriptionModel.id == jd_id, JobDescriptionModel.updated_at == payload.expected_updated_at)
        .values(**values, updated_at=func.now())
    )
    execution = await session.execute(statement)
    if getattr(execution, "rowcount", 0) != 1:
        await session.rollback()
        return APIResponse(code=1003, message="JD was changed by another editor; refresh and reconcile")
    await session.commit()
    # Core UPDATE may expire attributes in the identity map; refresh asynchronously
    # before serializing so this route never performs implicit sync I/O.
    await session.refresh(jd)
    return APIResponse(data=_jd_to_dict(jd))


@router.post("/{jd_id}/retry", response_model=APIResponse)
async def retry_jd(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=1002, message="Job description not found")
    if jd.status != JDStatus.FAILED.value:
        return APIResponse(code=1003, message="Only failed job descriptions can be retried")
    jd.processing_run_id = uuid.uuid4()
    jd.status = JDStatus.PROCESSING.value
    jd.processing_error = None
    start_step = jd.processing_step if jd.processing_step == JDProcessingStep.LLM_EXTRACT.value else None
    jd.processing_step = start_step or JDProcessingStep.QUEUED.value
    await session.commit()
    result = await JDImportService().dispatch_existing(session, jd, start_step=start_step)
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
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=1002, message="Job description not found")
    if jd.status != JDStatus.READY.value:
        return APIResponse(code=1003, message="Only ready job descriptions can be re-extracted")
    jd.processing_run_id = uuid.uuid4()
    jd.status = JDStatus.PROCESSING.value
    jd.processing_step = JDProcessingStep.LLM_EXTRACT.value
    jd.processing_error = None
    await session.commit()
    result = await JDImportService().dispatch_existing(
        session,
        jd,
        start_step=JDProcessingStep.LLM_EXTRACT.value,
        overwrite_manual=payload.overwrite_manual,
    )
    return _import_result_response(result)


@router.post("/{jd_id}/duplicate/confirm", response_model=APIResponse)
async def confirm_jd_duplicate(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    gate = await _require_llm(session)
    if gate is not None:
        return gate
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=1002, message="Job description not found")
    if jd.status != JDStatus.DUPLICATE_PENDING.value:
        return APIResponse(code=1003, message="Job description is not awaiting a duplicate decision")
    jd.processing_run_id = uuid.uuid4()
    jd.status = JDStatus.PROCESSING.value
    jd.processing_step = JDProcessingStep.LLM_EXTRACT.value
    jd.processing_error = None
    await session.commit()
    result = await JDImportService().dispatch_existing(
        session,
        jd,
        allow_duplicate=True,
        start_step=JDProcessingStep.LLM_EXTRACT.value,
    )
    return _import_result_response(result)


@router.post("/{jd_id}/duplicate/cancel", response_model=APIResponse)
async def cancel_jd_duplicate(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=1002, message="Job description not found")
    if jd.status != JDStatus.DUPLICATE_PENDING.value:
        return APIResponse(code=1003, message="Job description is not awaiting a duplicate decision")
    await _delete_jd(session, jd)
    return APIResponse(message="Duplicate job description cancelled")


@router.delete("/{jd_id}", response_model=APIResponse)
async def delete_job_description(jd_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> APIResponse:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        return APIResponse(code=1002, message="Job description not found")
    if await _jd_has_plan_reference(session, jd_id):
        return APIResponse(code=1005, message="Job description is referenced by a plan")
    try:
        await _delete_jd(session, jd)
    except IntegrityError:
        await session.rollback()
        return APIResponse(code=1005, message="Job description is referenced by a plan")
    return APIResponse(message="Job description deleted")


async def _jd_has_plan_reference(session: AsyncSession, jd_id: uuid.UUID) -> bool:
    """The plan table lands in RIP-008; keep RIP-007 usable before that migration."""
    from backend.infrastructure.db import models

    plan_model = getattr(models, "JobSearchPlanModel", None)
    if plan_model is None:
        return False
    result = await session.execute(
        select(plan_model.id).where(plan_model.jd_id == jd_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _delete_jd(session: AsyncSession, jd: JobDescriptionModel) -> None:
    jd.processing_run_id = uuid.uuid4()
    file_record = await session.get(FileModel, jd.source_file_id) if jd.source_file_id else None
    await session.delete(jd)
    if file_record is not None:
        await session.delete(file_record)
    await session.commit()
    if file_record is not None:
        try:
            await asyncio.to_thread(delete_file, get_settings().MINIO_BUCKET_RESUMES, file_record.storage_path)
        except Exception:  # pragma: no cover - object cleanup is deliberately best effort.
            logger.exception("Could not remove JD source object", extra={"file_id": str(file_record.id)})


def _match_row_to_dict(row: JDMatchResultModel) -> dict[str, Any]:
    return JDMatchResultData(
        id=str(row.id),
        resume_id=str(row.resume_id),
        jd_id=str(row.jd_id),
        match_score=row.match_score,
        skill_match=row.skill_match,
        missing_skills=row.missing_skills,
        risk=row.risk,
        gap=row.gap,
        recommendation=row.recommendation,
        detail=row.detail,
        created_at=row.created_at,
    ).model_dump(mode="json")
