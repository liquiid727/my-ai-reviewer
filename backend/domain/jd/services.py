"""JD processing rules: source extraction, normalization, dedupe, and provenance."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import tempfile
import unicodedata
import uuid
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.llm_config_service import get_active_verified_config
from backend.config import get_settings
from backend.domain.jd.enums import STRUCTURED_FIELD_NAMES, JDProcessingStep, JDSourceType, JDStatus
from backend.domain.jd.schemas import JDExtraction
from backend.infrastructure.db.models import FileModel, JobDescriptionModel
from backend.infrastructure.extractors.jd_extractor import JDExtractionError, JDExtractor
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.parsers import get_parser
from backend.infrastructure.storage.minio_client import download_file
from backend.infrastructure.web.safe_fetcher import SafeWebFetcher, SafeWebFetchError


class JDProcessingError(ValueError):
    """Expected processing failure whose message is safe to return to clients."""

    def __init__(self, message: str, code: int = 5003) -> None:
        super().__init__(message)
        self.code = code


def normalize_jd_text(raw_text: str) -> str:
    """Create the canonical duplicate-detection representation of JD body text."""
    normalized = unicodedata.normalize("NFKC", raw_text).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", normalized).strip()


def content_hash(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def _extraction_values(extraction: JDExtraction) -> dict[str, object]:
    return {
        "title": extraction.title,
        "company": extraction.company,
        "location": extraction.location,
        "seniority": extraction.seniority,
        "responsibilities": extraction.responsibilities,
        "required_skills": [skill.model_dump() for skill in extraction.required_skills],
        "preferred_skills": [skill.model_dump() for skill in extraction.preferred_skills],
    }


class JDProcessingService:
    """Stateful worker operations guarded by a processing run UUID."""

    async def source_extract(self, session: AsyncSession, jd_id: uuid.UUID, run_id: uuid.UUID) -> str:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return "stale"
        if not await self._write_current(
            session,
            jd_id,
            run_id,
            {
                "status": JDStatus.PROCESSING.value,
                "processing_step": JDProcessingStep.SOURCE_EXTRACT.value,
                "processing_error": None,
            },
        ):
            return "stale"

        try:
            raw_text, parser_version = await self._read_source(session, jd)
            normalized = normalize_jd_text(raw_text)
            visible_chars = len(re.sub(r"\s", "", normalized))
            if visible_chars < 30:
                raise JDProcessingError("Job description content is too short to process")
            if len(normalized) > 100_000:
                raise JDProcessingError("Job description content is too large to process")
        except JDProcessingError:
            raise
        except (OSError, SafeWebFetchError, ValueError) as exc:
            raise JDProcessingError("Unable to extract readable job description content") from exc

        if not await self._write_current(
            session,
            jd_id,
            run_id,
            {
                "raw_text": normalized,
                "parser_version": parser_version,
                "processing_step": JDProcessingStep.DUPLICATE_CHECK.value,
            },
        ):
            return "stale"
        return "processing"

    async def duplicate_check(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        allow_duplicate: bool = False,
    ) -> str:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return "stale"
        if not jd.raw_text:
            raise JDProcessingError("Job description content is unavailable")

        digest = content_hash(jd.raw_text)
        if allow_duplicate:
            return (
                "processing"
                if await self._write_current(
                    session,
                    jd_id,
                    run_id,
                    {
                        "status": JDStatus.PROCESSING.value,
                        "processing_step": JDProcessingStep.LLM_EXTRACT.value,
                        "processing_error": None,
                        "content_hash": digest,
                        "duplicate_of_id": None,
                    },
                )
                else "stale"
            )

        user_scope = (
            JobDescriptionModel.user_id.is_(None)
            if jd.user_id is None
            else JobDescriptionModel.user_id == jd.user_id
        )
        stmt = (
            select(JobDescriptionModel.id)
            .where(
                JobDescriptionModel.id != jd.id,
                JobDescriptionModel.content_hash == digest,
                user_scope,
            )
            .order_by(JobDescriptionModel.created_at)
            .limit(1)
        )
        duplicate_id = (await session.execute(stmt)).scalar_one_or_none()
        if duplicate_id is not None:
            return (
                JDStatus.DUPLICATE_PENDING.value
                if await self._write_current(
                    session,
                    jd_id,
                    run_id,
                    {
                        "status": JDStatus.DUPLICATE_PENDING.value,
                        "processing_step": JDProcessingStep.DUPLICATE_CHECK.value,
                        "content_hash": digest,
                        "duplicate_of_id": duplicate_id,
                    },
                )
                else "stale"
            )

        return (
            "processing"
            if await self._write_current(
                session,
                jd_id,
                run_id,
                {
                    "status": JDStatus.PROCESSING.value,
                    "processing_step": JDProcessingStep.LLM_EXTRACT.value,
                    "processing_error": None,
                    "content_hash": digest,
                    "duplicate_of_id": None,
                },
            )
            else "stale"
        )

    async def llm_extract(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        overwrite_manual: bool = False,
    ) -> str:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return "stale"
        if not jd.raw_text:
            raise JDProcessingError("Job description content is unavailable")
        raw_text = jd.raw_text
        if not await self._write_current(
            session,
            jd_id,
            run_id,
            {
                "status": JDStatus.PROCESSING.value,
                "processing_step": JDProcessingStep.LLM_EXTRACT.value,
                "processing_error": None,
            },
        ):
            return "stale"

        config = await get_active_verified_config(session)
        if config is None:
            await session.rollback()
            raise JDProcessingError("LLM not configured or not verified", code=428)
        extractor = JDExtractor(LLMGateway.from_config(config))
        # Configuration has been copied into the gateway; do not hold a database
        # transaction while waiting on the provider.
        await session.rollback()
        try:
            extraction = await extractor.extract(raw_text)
        except JDExtractionError as exc:
            raise JDProcessingError("JD structured extraction failed", code=5001) from exc
        except Exception as exc:
            # Keep provider payloads and credentials out of worker-visible state.
            raise JDProcessingError("JD structured extraction failed", code=5001) from exc

        current = await self._current_jd(session, jd_id, run_id)
        if current is None:
            return "stale"
        values = self._merged_extraction_values(current, extraction, overwrite_manual=overwrite_manual)
        values.update(
            {
                "status": JDStatus.READY.value,
                "processing_step": JDProcessingStep.DONE.value,
                "processing_error": None,
            }
        )
        if not await self._write_current(session, jd_id, run_id, values):
            return "stale"
        return JDStatus.READY.value

    async def mark_failed(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        run_id: uuid.UUID,
        step: str,
        error: JDProcessingError | Exception,
    ) -> None:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return
        await self._write_current(
            session,
            jd_id,
            run_id,
            {
                "status": JDStatus.FAILED.value,
                "processing_step": step,
                "processing_error": str(error) if isinstance(error, JDProcessingError) else "JD processing failed",
            },
        )

    @staticmethod
    def _merge_extraction(
        jd: JobDescriptionModel,
        extraction: JDExtraction,
        *,
        overwrite_manual: bool,
    ) -> None:
        for field, value in JDProcessingService._merged_extraction_values(
            jd,
            extraction,
            overwrite_manual=overwrite_manual,
        ).items():
            setattr(jd, field, value)

    @staticmethod
    def _merged_extraction_values(
        jd: JobDescriptionModel,
        extraction: JDExtraction,
        *,
        overwrite_manual: bool,
    ) -> dict[str, object]:
        sources = dict(jd.field_sources or {})
        values: dict[str, object] = {}
        for field, value in _extraction_values(extraction).items():
            if field not in STRUCTURED_FIELD_NAMES:
                continue
            if sources.get(field) == "manual" and not overwrite_manual:
                continue
            values[field] = value
            sources[field] = "llm"
        values["field_sources"] = sources
        values["extraction_source"] = "llm"
        return values

    async def _read_source(self, session: AsyncSession, jd: JobDescriptionModel) -> tuple[str, str]:
        if jd.source_type == JDSourceType.TEXT.value:
            return jd.raw_text, "direct-text-v1"
        if jd.source_type == JDSourceType.URL.value:
            if not jd.source_url:
                raise JDProcessingError("URL source is missing")
            return await SafeWebFetcher().fetch_text(jd.source_url), "safe-web-v1"
        if jd.source_type != JDSourceType.FILE.value or jd.source_file_id is None:
            raise JDProcessingError("File source is missing")

        file_record = await session.get(FileModel, jd.source_file_id)
        if file_record is None:
            raise JDProcessingError("Source file is unavailable")
        storage_path = file_record.storage_path
        original_name = file_record.original_name
        # The row is only a source snapshot. Release its read transaction before
        # object storage and parser work, which can be slow or fail externally.
        await session.rollback()
        data = await asyncio.to_thread(
            download_file,
            get_settings().MINIO_BUCKET_RESUMES,
            storage_path,
        )
        extension = Path(original_name).suffix.lower()
        if extension not in {".pdf", ".docx", ".txt", ".md"}:
            raise JDProcessingError("Source file type is not supported")
        temporary_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temporary_file:
                temporary_file.write(data)
                temporary_path = temporary_file.name
            parser = get_parser(extension)
            parsed = await asyncio.to_thread(parser.parse, temporary_path)
            return parsed.raw_text, parser.version
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    @staticmethod
    async def _current_jd(
        session: AsyncSession,
        jd_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> JobDescriptionModel | None:
        jd = await session.get(JobDescriptionModel, jd_id)
        return jd if jd is not None and JDProcessingService._matches_run(jd, run_id) else None

    @staticmethod
    async def _write_current(
        session: AsyncSession,
        jd_id: uuid.UUID,
        run_id: uuid.UUID,
        values: dict[str, object],
    ) -> bool:
        """Write only when this worker's run is still the current run."""
        result = await session.execute(
            update(JobDescriptionModel)
            .where(
                JobDescriptionModel.id == jd_id,
                JobDescriptionModel.processing_run_id == run_id,
            )
            .values(**values)
        )
        if getattr(result, "rowcount", 0) != 1:
            await session.rollback()
            return False
        await session.commit()
        return True

    @staticmethod
    def _matches_run(jd: JobDescriptionModel, run_id: uuid.UUID) -> bool:
        return jd.processing_run_id == run_id
