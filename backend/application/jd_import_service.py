"""Application service for durable JD imports and broker handoff."""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath

from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.jd.enums import JDProcessingStep, JDSourceType, JDStatus
from backend.domain.jd.policies import content_hash, normalize_jd_text
from backend.domain.jd.schemas import JDManualImportRequest
from backend.infrastructure.db.models import FileModel, JobDescriptionModel
from backend.infrastructure.storage.minio_client import delete_file, upload_file

logger = logging.getLogger(__name__)

MAX_JD_FILE_SIZE = 10 * 1024 * 1024
JD_FILE_CONTENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
}
JD_IMAGE_CONTENT_TYPES: dict[str, set[str]] = {
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}
JD_IMAGE_MAGIC: dict[str, bytes] = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}
# Decode bounds: reject pathological images before PIL expands them.
MAX_IMAGE_DIMENSION = 16_000
MAX_IMAGE_PIXELS = 60_000_000
MIN_IMAGE_DIMENSION = 1


class JDImportError(ValueError):
    """A safe API error with an application-specific response code."""

    def __init__(self, message: str, code: int = 1001) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class JDImportResult:
    jd: JobDescriptionModel
    dispatch_failed: bool = False


def _file_extension(filename: str) -> str:
    extension = PurePosixPath(filename).suffix.lower()
    if extension not in JD_FILE_CONTENT_TYPES:
        raise JDImportError("Only PDF, DOCX, TXT, and Markdown files are supported")
    return extension


def _validate_file(filename: str, content_type: str | None, data: bytes) -> str:
    extension = _file_extension(filename)
    if not data:
        raise JDImportError("File must not be empty")
    if len(data) > MAX_JD_FILE_SIZE:
        raise JDImportError("File is larger than 10MB")
    if content_type and content_type.lower() not in JD_FILE_CONTENT_TYPES[extension]:
        raise JDImportError("File MIME type does not match its extension")
    return extension


def _image_extension(filename: str) -> str:
    extension = PurePosixPath(filename).suffix.lower()
    if extension not in JD_IMAGE_CONTENT_TYPES:
        raise JDImportError("Only PNG and JPEG image files are supported")
    return extension


def _validate_image(filename: str, content_type: str | None, data: bytes) -> str:
    extension = _image_extension(filename)
    if not data:
        raise JDImportError("Image file must not be empty")
    if len(data) > MAX_JD_FILE_SIZE:
        raise JDImportError("Image is larger than 10MB", code=413)
    if content_type and content_type.lower() not in JD_IMAGE_CONTENT_TYPES[extension]:
        raise JDImportError("Image MIME type does not match its extension")
    if not data.startswith(JD_IMAGE_MAGIC[extension]):
        raise JDImportError("Image content does not match its extension")
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                raise JDImportError("Image has invalid dimensions")
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise JDImportError("Image dimensions exceed the allowed bound", code=413)
            if width * height > MAX_IMAGE_PIXELS:
                raise JDImportError("Image pixel count exceeds the allowed bound", code=413)
            image.verify()
    except JDImportError:
        raise
    except Exception as exc:
        raise JDImportError("Image cannot be decoded") from exc
    return extension


def _manual_sources(*fields: str) -> dict[str, str]:
    return {field: "manual" for field in fields}


def _draft_item(key: str, value: str, *, category: str | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "key": key,
        "value": value,
        "evidence": None,
        "evidence_status": "unavailable",
        "confidence": 1.0,
        "provenance": "manual",
    }
    if category is not None:
        item["category"] = category
    return item


def _manual_review_draft(payload: JDManualImportRequest) -> dict[str, object]:
    """Project manual input into the RIP-011 review draft without an LLM.

    Provenance is `manual` for every field, confidence is 1.0, and no evidence
    or source quote is fabricated. The scalar `title`/`company` fields stay
    JSON scalars; lists use DraftItem shape so the review/publish lifecycle
    consumes them directly.
    """
    return {
        "title": payload.title.strip(),
        "company": payload.company.strip() if payload.company else None,
        "department": payload.department.strip() if payload.department else None,
        "location": payload.location.strip() if payload.location else None,
        "employment_type": payload.employment_type,
        "responsibilities": [
            _draft_item(f"manual-{index}", value) for index, value in enumerate(payload.responsibilities)
        ],
        "required_skills": [
            {
                **_draft_item(f"manual-{index}", skill.name),
                "critical": skill.critical,
            }
            for index, skill in enumerate(payload.required_skills)
        ],
        "preferred_skills": [
            {
                **_draft_item(f"manual-{index}", skill.name),
                "critical": skill.critical,
            }
            for index, skill in enumerate(payload.preferred_skills)
        ],
        "notes": payload.notes.strip() if payload.notes else None,
        "parser_version": None,
        "model_name": None,
        "prompt_version": None,
        "schema_version": "jd-review-v1",
        "overall_confidence": 1.0,
    }


def _manual_text(payload: JDManualImportRequest) -> str:
    lines = [
        payload.title.strip(),
        payload.company.strip() if payload.company else "",
        payload.department.strip() if payload.department else "",
        payload.location.strip() if payload.location else "",
        *(skill.name for skill in payload.required_skills),
        *(skill.name for skill in payload.preferred_skills),
        *payload.responsibilities,
    ]
    return normalize_jd_text(" ".join(line for line in lines if line))


class JDImportService:
    """Create queued records, persist files, and dispatch one JD processing run."""

    async def import_text(
        self,
        session: AsyncSession,
        *,
        raw_text: str,
        title: str | None = None,
        company: str | None = None,
        allow_duplicate: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> JDImportResult:
        text = raw_text.strip()
        if not text or len(text) > 100_000:
            raise JDImportError("JD text must contain between 1 and 100000 characters")
        manual = _manual_sources(*(name for name, value in (("title", title), ("company", company)) if value))
        jd = JobDescriptionModel(
            user_id=user_id,
            source_type=JDSourceType.TEXT.value,
            raw_text=text,
            title=title,
            company=company,
            field_sources=manual,
            status=JDStatus.PROCESSING.value,
            processing_step=JDProcessingStep.QUEUED.value,
            processing_run_id=uuid.uuid4(),
        )
        session.add(jd)
        await session.commit()
        return await self._dispatch_or_mark_failed(session, jd, allow_duplicate=allow_duplicate)

    async def import_file(
        self,
        session: AsyncSession,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
        allow_duplicate: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> JDImportResult:
        extension = _validate_file(filename, content_type, data)
        jd = JobDescriptionModel(
            user_id=user_id,
            source_type=JDSourceType.FILE.value,
            raw_text="",
            status=JDStatus.PROCESSING.value,
            processing_step=JDProcessingStep.QUEUED.value,
            processing_run_id=uuid.uuid4(),
        )
        session.add(jd)
        await session.flush()

        settings = get_settings()
        owner_id = user_id or uuid.uuid4()
        owner_key = str(user_id) if user_id else "anonymous"
        object_name = f"jd/{owner_key}/{jd.id}/{uuid.uuid4()}{extension}"
        uploaded = False
        try:
            await asyncio.to_thread(
                upload_file,
                settings.MINIO_BUCKET_RESUMES,
                object_name,
                data,
                content_type or "application/octet-stream",
            )
            uploaded = True
            file_record = FileModel(
                original_name=filename,
                storage_path=object_name,
                content_type=content_type or "application/octet-stream",
                size_bytes=len(data),
                sha256_hash=hashlib.sha256(data).hexdigest(),
                owner_type="job_description",
                owner_id=owner_id,
            )
            session.add(file_record)
            await session.flush()
            jd.source_file_id = file_record.id
            await session.commit()
        except Exception as exc:
            await session.rollback()
            if uploaded:
                try:
                    await asyncio.to_thread(delete_file, settings.MINIO_BUCKET_RESUMES, object_name)
                except Exception:  # pragma: no cover - best effort compensation.
                    logger.exception("Could not compensate failed JD file import", extra={"object_name": object_name})
            raise JDImportError("Unable to store JD file", code=5003) from exc
        return await self._dispatch_or_mark_failed(session, jd, allow_duplicate=allow_duplicate)

    async def import_image(
        self,
        session: AsyncSession,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
        allow_duplicate: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> JDImportResult:
        extension = _validate_image(filename, content_type, data)
        jd = JobDescriptionModel(
            user_id=user_id,
            source_type=JDSourceType.IMAGE.value,
            raw_text="",
            status=JDStatus.PROCESSING.value,
            processing_step=JDProcessingStep.QUEUED.value,
            processing_run_id=uuid.uuid4(),
        )
        session.add(jd)
        await session.flush()

        settings = get_settings()
        owner_key = str(user_id) if user_id else "anonymous"
        object_name = f"jd/{owner_key}/{jd.id}/{uuid.uuid4()}{extension}"
        uploaded = False
        try:
            await asyncio.to_thread(
                upload_file,
                settings.MINIO_BUCKET_RESUMES,
                object_name,
                data,
                content_type or ("image/png" if extension == ".png" else "image/jpeg"),
            )
            uploaded = True
            file_record = FileModel(
                original_name=filename,
                storage_path=object_name,
                content_type=content_type or ("image/png" if extension == ".png" else "image/jpeg"),
                size_bytes=len(data),
                sha256_hash=hashlib.sha256(data).hexdigest(),
                owner_type="job_description",
                owner_id=user_id or uuid.uuid4(),
            )
            session.add(file_record)
            await session.flush()
            jd.source_file_id = file_record.id
            await session.commit()
        except Exception as exc:
            await session.rollback()
            if uploaded:
                try:
                    await asyncio.to_thread(delete_file, settings.MINIO_BUCKET_RESUMES, object_name)
                except Exception:  # pragma: no cover - best effort compensation.
                    logger.exception("Could not compensate failed JD image import", extra={"object_name": object_name})
            raise JDImportError("Unable to store JD image", code=5003) from exc
        return await self._dispatch_or_mark_failed(session, jd, allow_duplicate=allow_duplicate)

    async def create_manual(
        self,
        session: AsyncSession,
        *,
        payload: JDManualImportRequest,
        user_id: uuid.UUID | None = None,
    ) -> JDImportResult:
        """Create a manual JD synchronously and enter review with no LLM call."""
        title = payload.title.strip()
        if not title:
            raise JDImportError("Manual JD requires a title")
        raw_text = _manual_text(payload)
        digest = content_hash(raw_text)
        duplicate = None
        if not payload.allow_duplicate:
            duplicate = await self._find_manual_duplicate(session, digest, user_id)
        sources = _manual_sources(
            *(name for name, value in (("title", title), ("company", payload.company)) if value)
        )
        jd = JobDescriptionModel(
            user_id=user_id,
            source_type=JDSourceType.MANUAL.value,
            raw_text=raw_text,
            title=title,
            company=payload.company.strip() if payload.company else None,
            location=payload.location.strip() if payload.location else None,
            extraction_source="manual",
            field_sources=sources,
            status=JDStatus.NEEDS_REVIEW.value,
            processing_step=JDProcessingStep.REVIEW.value,
            review_revision=1,
            review_draft=_manual_review_draft(payload),
            content_hash=digest,
        )
        if duplicate is not None:
            jd.status = JDStatus.DUPLICATE_PENDING.value
            jd.processing_step = JDProcessingStep.DUPLICATE_CHECK.value
            jd.duplicate_of_id = duplicate
        session.add(jd)
        await session.commit()
        await session.refresh(jd)
        return JDImportResult(jd=jd)

    @staticmethod
    async def _find_manual_duplicate(
        session: AsyncSession,
        digest: str,
        user_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        """Earliest JD in the user scope with the same canonical hash (RIP-012 §6.3).

        The worker pipeline normally owns duplicate detection; manual creation is
        synchronous, so the check happens inline before the review row is written.
        """
        user_scope = (
            JobDescriptionModel.user_id.is_(None) if user_id is None else JobDescriptionModel.user_id == user_id
        )
        stmt = (
            select(JobDescriptionModel.id)
            .where(JobDescriptionModel.content_hash == digest, user_scope)
            .order_by(JobDescriptionModel.created_at)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def import_url(
        self,
        session: AsyncSession,
        *,
        url: str,
        allow_duplicate: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> JDImportResult:
        jd = JobDescriptionModel(
            user_id=user_id,
            source_type=JDSourceType.URL.value,
            source_url=url,
            raw_text="",
            status=JDStatus.PROCESSING.value,
            processing_step=JDProcessingStep.QUEUED.value,
            processing_run_id=uuid.uuid4(),
        )
        session.add(jd)
        await session.commit()
        return await self._dispatch_or_mark_failed(session, jd, allow_duplicate=allow_duplicate)

    async def dispatch_existing(
        self,
        session: AsyncSession,
        jd: JobDescriptionModel,
        *,
        allow_duplicate: bool = False,
        start_step: str | None = None,
        overwrite_manual: bool = False,
    ) -> JDImportResult:
        """Queue a run that was prepared by a retry/re-extract command."""
        return await self._dispatch_or_mark_failed(
            session,
            jd,
            allow_duplicate=allow_duplicate,
            start_step=start_step,
            overwrite_manual=overwrite_manual,
        )

    async def _dispatch_or_mark_failed(
        self,
        session: AsyncSession,
        jd: JobDescriptionModel,
        *,
        allow_duplicate: bool,
        start_step: str | None = None,
        overwrite_manual: bool = False,
    ) -> JDImportResult:
        run_id = jd.processing_run_id
        assert run_id is not None
        try:
            from backend.tasks.jd_tasks import process_jd_pipeline

            await asyncio.to_thread(
                process_jd_pipeline,
                str(jd.id),
                str(run_id),
                allow_duplicate,
                start_step,
                overwrite_manual,
            )
        except Exception:
            result = await session.execute(
                update(JobDescriptionModel)
                .where(
                    JobDescriptionModel.id == jd.id,
                    JobDescriptionModel.processing_run_id == run_id,
                )
                .values(
                    status=JDStatus.FAILED.value,
                    processing_step=start_step or JDProcessingStep.QUEUED.value,
                    processing_error="Unable to dispatch JD processing. Please retry.",
                )
            )
            if getattr(result, "rowcount", 0) == 1:
                await session.commit()
                await session.refresh(jd)
            else:
                await session.rollback()
            return JDImportResult(jd=jd, dispatch_failed=True)
        return JDImportResult(jd=jd)
