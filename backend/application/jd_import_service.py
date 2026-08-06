"""Application service for durable JD imports and broker handoff."""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.jd.enums import JDProcessingStep, JDSourceType, JDStatus
from backend.infrastructure.db.models import FileModel, JDSourceAssetModel, JobDescriptionModel
from backend.infrastructure.storage.minio_client import delete_file, upload_file

logger = logging.getLogger(__name__)

MAX_JD_FILE_SIZE = 10 * 1024 * 1024
MAX_JD_IMAGE_SIZE = 10 * 1024 * 1024
MAX_JD_IMAGE_TOTAL_SIZE = 30 * 1024 * 1024
MAX_JD_IMAGE_COUNT = 8
MAX_JD_IMAGE_PIXELS = 25_000_000
MAX_JD_IMAGE_EDGE = 4_000
JD_FILE_CONTENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
}


JD_IMAGE_CONTENT_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class JDImportError(ValueError):
    """A safe API error with an application-specific response code."""

    def __init__(self, message: str, code: int = 1001) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class JDImageInput:
    filename: str
    content_type: str | None
    data: bytes


@dataclass(frozen=True)
class SanitizedJDImage:
    original_name: str
    media_type: str
    data: bytes
    width: int
    height: int
    content_hash: str


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
        raise JDImportError("Only PNG, JPG/JPEG, and WEBP images are supported")
    return extension


def _magic_media_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_and_sanitize_images(images: list[JDImageInput]) -> list[SanitizedJDImage]:
    if not images:
        raise JDImportError("At least one image is required")
    if len(images) > MAX_JD_IMAGE_COUNT:
        raise JDImportError("At most 8 images are supported")
    total = sum(len(image.data) for image in images)
    if total > MAX_JD_IMAGE_TOTAL_SIZE:
        raise JDImportError("Total image size is larger than 30MB")
    sanitized: list[SanitizedJDImage] = []
    for image in images:
        extension = _image_extension(image.filename)
        expected_media_type = JD_IMAGE_CONTENT_TYPES[extension]
        declared = (image.content_type or expected_media_type).lower()
        if declared != expected_media_type:
            raise JDImportError("Image MIME type does not match its extension")
        if not image.data:
            raise JDImportError("Image must not be empty")
        if len(image.data) > MAX_JD_IMAGE_SIZE:
            raise JDImportError("Image is larger than 10MB")
        magic = _magic_media_type(image.data)
        if magic != expected_media_type:
            raise JDImportError("Image bytes do not match the declared format")
        try:
            with Image.open(io.BytesIO(image.data)) as opened:
                opened.verify()
            with Image.open(io.BytesIO(image.data)) as opened:
                normalized = ImageOps.exif_transpose(opened)
                if normalized.width * normalized.height > MAX_JD_IMAGE_PIXELS:
                    raise JDImportError("Image exceeds the 25MP limit")
                if max(normalized.width, normalized.height) > MAX_JD_IMAGE_EDGE:
                    raise JDImportError("Image maximum edge exceeds 4000px")
                clean = Image.new(normalized.mode, normalized.size)
                clean.putdata(list(normalized.getdata()))
                if expected_media_type == "image/jpeg" and clean.mode not in {"RGB", "L"}:
                    clean = clean.convert("RGB")
                output = io.BytesIO()
                format_name = "JPEG" if expected_media_type == "image/jpeg" else opened.format
                if format_name is None:
                    format_name = "PNG" if expected_media_type == "image/png" else "WEBP"
                clean.save(output, format=format_name)
                data = output.getvalue()
                sanitized.append(
                    SanitizedJDImage(
                        original_name=image.filename,
                        media_type=expected_media_type,
                        data=data,
                        width=normalized.width,
                        height=normalized.height,
                        content_hash=hashlib.sha256(data).hexdigest(),
                    )
                )
        except JDImportError:
            raise
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise JDImportError("Image is corrupted or unsupported") from exc
    return sanitized


def _manual_sources(*fields: str) -> dict[str, str]:
    return {field: "manual" for field in fields}


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

    async def import_images(
        self,
        session: AsyncSession,
        *,
        images: list[JDImageInput],
        acknowledge_external_vision: bool,
        title: str | None = None,
        company: str | None = None,
        allow_duplicate: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> JDImportResult:
        if not acknowledge_external_vision:
            raise JDImportError("External Vision provider acknowledgement is required")
        sanitized = validate_and_sanitize_images(images)
        manual = _manual_sources(*(name for name, value in (("title", title), ("company", company)) if value))
        jd = JobDescriptionModel(
            user_id=user_id,
            title=title,
            company=company,
            source_type=JDSourceType.IMAGE.value,
            raw_text="",
            field_sources=manual,
            status=JDStatus.PROCESSING.value,
            processing_step=JDProcessingStep.SOURCE_VALIDATE.value,
            processing_run_id=uuid.uuid4(),
            source_asset_count=len(sanitized),
        )
        session.add(jd)
        await session.flush()
        settings = get_settings()
        owner_id = user_id or uuid.uuid4()
        owner_key = str(user_id) if user_id else "anonymous"
        uploaded_objects: list[str] = []
        try:
            for order_index, image in enumerate(sanitized):
                extension = (
                    ".jpg"
                    if image.media_type == "image/jpeg"
                    else ".png"
                    if image.media_type == "image/png"
                    else ".webp"
                )
                object_name = f"jd/{owner_key}/{jd.id}/image-{order_index:02d}-{uuid.uuid4()}{extension}"
                await asyncio.to_thread(
                    upload_file, settings.MINIO_BUCKET_RESUMES, object_name, image.data, image.media_type
                )
                uploaded_objects.append(object_name)
                file_record = FileModel(
                    original_name=image.original_name,
                    storage_path=object_name,
                    content_type=image.media_type,
                    size_bytes=len(image.data),
                    sha256_hash=image.content_hash,
                    owner_type="job_description_image",
                    owner_id=owner_id,
                )
                session.add(file_record)
                await session.flush()
                session.add(
                    JDSourceAssetModel(
                        jd_id=jd.id,
                        file_id=file_record.id,
                        order_index=order_index,
                        media_type=image.media_type,
                        byte_size=len(image.data),
                        width=image.width,
                        height=image.height,
                        content_hash=image.content_hash,
                        status="stored",
                    )
                )
            await session.commit()
        except Exception as exc:
            await session.rollback()
            for object_name in uploaded_objects:
                try:
                    await asyncio.to_thread(delete_file, settings.MINIO_BUCKET_RESUMES, object_name)
                except Exception:
                    logger.exception("Could not compensate failed JD image import", extra={"object_name": object_name})
            if isinstance(exc, JDImportError):
                raise
            raise JDImportError("Unable to store JD image", code=5003) from exc
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
                jd.source_type,
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
