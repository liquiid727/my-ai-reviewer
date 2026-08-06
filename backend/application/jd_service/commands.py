"""JD command use cases: match, legacy create, patch, retry, reextract, delete."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_import_service import JDImportResult, JDImportService
from backend.application.jd_service.matching import JDMatchingService
from backend.application.jd_service.queries import serialize_jd, serialize_match
from backend.config import get_settings
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.domain.jd.schemas import JobDescriptionInput
from backend.infrastructure.db.models import FileModel, JobDescriptionModel, ResumeModel
from backend.infrastructure.extractors.jd_extractor import JDExtractionError, JDExtractor
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.storage.minio_client import delete_file

logger = logging.getLogger(__name__)

_LIST_FIELDS = {"responsibilities", "required_skills", "preferred_skills"}


class JDCommandError(Exception):
    """Command failure with API-facing code/message."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class MatchCommandResult:
    payload: dict[str, Any]


@dataclass(frozen=True)
class LegacyCreateResult:
    payload: dict[str, Any]


def _get_legacy_extractor() -> JDExtractor:
    """Build the legacy extractor from settings; old POST /jd remains compatible."""
    return JDExtractor(gateway=LLMGateway.from_settings())


async def match_resume(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    jd_id: uuid.UUID | None,
    jd_input: JobDescriptionInput | None,
) -> MatchCommandResult:
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise JDCommandError("Resume not found", 404)

    if jd_id is not None:
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDCommandError("Job description not found", 404)
        if jd.status != JDStatus.READY.value:
            raise JDCommandError("Job description is not ready", 1003)
    elif jd_input is not None:
        required_skills = [
            {"name": name, "critical": name in (jd_input.critical_skills or [])} for name in jd_input.required_skills
        ]
        jd = JobDescriptionModel(
            title=jd_input.title,
            company=jd_input.company,
            raw_text=jd_input.raw_text,
            required_skills=required_skills,
        )
        session.add(jd)
        await session.flush()
    else:
        raise JDCommandError("Either jd_id or jd must be provided", 400)

    record = await JDMatchingService().match(session, resume_id, jd)
    await session.commit()
    return MatchCommandResult(payload=serialize_match(record))


async def create_legacy_job_description(
    session: AsyncSession,
    payload: JobDescriptionInput,
    *,
    extractor: JDExtractor | Any | None = None,
) -> LegacyCreateResult:
    """Legacy synchronous create endpoint retained for existing matching callers."""
    responsibilities: list[str] = []
    seniority: str | None = None
    extraction_source = "manual"
    skills_explicit = "required_skills" in payload.model_fields_set

    if payload.required_skills:
        required_skills = [
            {"name": name, "critical": name in (payload.critical_skills or [])} for name in payload.required_skills
        ]
    elif not skills_explicit and payload.raw_text.strip():
        if extractor is None:
            active = _get_legacy_extractor()
        elif callable(extractor) and not hasattr(extractor, "extract"):
            active = extractor()
        else:
            active = extractor
        try:
            extraction = await active.extract(payload.raw_text)
        except JDExtractionError as exc:
            raise JDCommandError("JD_EXTRACTION_FAILED", 502) from exc
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
        structured_revision=1,
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
    return LegacyCreateResult(payload=serialize_jd(jd))


async def patch_job_description(
    session: AsyncSession,
    jd_id: uuid.UUID,
    *,
    changed_fields: set[str],
    field_values: dict[str, Any],
    expected_updated_at: datetime,
) -> dict[str, Any]:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        raise JDCommandError("Job description not found", 1002)
    if not changed_fields:
        return serialize_jd(jd)

    fields = dict(jd.field_sources or {})
    values: dict[str, Any] = {}
    for field in changed_fields:
        value = field_values[field]
        if field in _LIST_FIELDS:
            values[field] = (
                [] if value is None else [item.model_dump() if hasattr(item, "model_dump") else item for item in value]
            )
        else:
            values[field] = value
        fields[field] = "manual"
    values["field_sources"] = fields
    values["structured_revision"] = JobDescriptionModel.structured_revision + 1

    statement = (
        update(JobDescriptionModel)
        .where(JobDescriptionModel.id == jd_id, JobDescriptionModel.updated_at == expected_updated_at)
        .values(**values, updated_at=func.now())
    )
    execution = await session.execute(statement)
    if getattr(execution, "rowcount", 0) != 1:
        await session.rollback()
        raise JDCommandError("JD was changed by another editor; refresh and reconcile", 1003)
    await session.commit()
    await session.refresh(jd)
    return serialize_jd(jd)


async def retry_jd(session: AsyncSession, jd_id: uuid.UUID) -> JDImportResult:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        raise JDCommandError("Job description not found", 1002)
    if jd.status != JDStatus.FAILED.value:
        raise JDCommandError("Only failed job descriptions can be retried", 1003)
    jd.processing_run_id = uuid.uuid4()
    jd.status = JDStatus.PROCESSING.value
    jd.processing_error = None
    start_step = jd.processing_step if jd.processing_step == JDProcessingStep.LLM_EXTRACT.value else None
    jd.processing_step = start_step or JDProcessingStep.QUEUED.value
    await session.commit()
    return await JDImportService().dispatch_existing(session, jd, start_step=start_step)


async def reextract_jd(
    session: AsyncSession,
    jd_id: uuid.UUID,
    *,
    overwrite_manual: bool,
) -> JDImportResult:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        raise JDCommandError("Job description not found", 1002)
    if jd.status != JDStatus.READY.value:
        raise JDCommandError("Only ready job descriptions can be re-extracted", 1003)
    jd.processing_run_id = uuid.uuid4()
    jd.status = JDStatus.PROCESSING.value
    jd.processing_step = JDProcessingStep.LLM_EXTRACT.value
    jd.processing_error = None
    await session.commit()
    return await JDImportService().dispatch_existing(
        session,
        jd,
        start_step=JDProcessingStep.LLM_EXTRACT.value,
        overwrite_manual=overwrite_manual,
    )


async def confirm_duplicate(session: AsyncSession, jd_id: uuid.UUID) -> JDImportResult:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        raise JDCommandError("Job description not found", 1002)
    if jd.status != JDStatus.DUPLICATE_PENDING.value:
        raise JDCommandError("Job description is not awaiting a duplicate decision", 1003)
    jd.processing_run_id = uuid.uuid4()
    jd.status = JDStatus.PROCESSING.value
    jd.processing_step = JDProcessingStep.LLM_EXTRACT.value
    jd.processing_error = None
    await session.commit()
    return await JDImportService().dispatch_existing(
        session,
        jd,
        allow_duplicate=True,
        start_step=JDProcessingStep.LLM_EXTRACT.value,
    )


async def cancel_duplicate(session: AsyncSession, jd_id: uuid.UUID) -> None:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        raise JDCommandError("Job description not found", 1002)
    if jd.status != JDStatus.DUPLICATE_PENDING.value:
        raise JDCommandError("Job description is not awaiting a duplicate decision", 1003)
    await delete_jd(session, jd)


async def delete_job_description(session: AsyncSession, jd_id: uuid.UUID) -> None:
    jd = await session.get(JobDescriptionModel, jd_id)
    if jd is None:
        raise JDCommandError("Job description not found", 1002)
    if await jd_has_plan_reference(session, jd_id):
        raise JDCommandError("Job description is referenced by a plan", 1005)
    try:
        await delete_jd(session, jd)
    except IntegrityError as exc:
        await session.rollback()
        raise JDCommandError("Job description is referenced by a plan", 1005) from exc


async def jd_has_plan_reference(session: AsyncSession, jd_id: uuid.UUID) -> bool:
    """The plan table lands in RIP-008; keep RIP-007 usable before that migration."""
    from backend.infrastructure.db import models

    plan_model = getattr(models, "JobSearchPlanModel", None)
    if plan_model is None:
        return False
    result = await session.execute(select(plan_model.id).where(plan_model.jd_id == jd_id).limit(1))
    return result.scalar_one_or_none() is not None


async def delete_jd(session: AsyncSession, jd: JobDescriptionModel) -> None:
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
