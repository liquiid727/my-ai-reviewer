"""JD processing use cases: source extract, duplicate check, LLM extract."""

from __future__ import annotations

import asyncio
import base64
import os
import re
import tempfile
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.llm_config_service import get_active_verified_config
from backend.config import get_settings
from backend.domain.jd.enums import JDProcessingStep, JDSourceType, JDStatus
from backend.domain.jd.policies import (
    JDProcessingError,
    content_hash,
    draft_from_extraction,
    merged_extraction_values,
    normalize_jd_text,
)
from backend.domain.jd.schemas import JDExtraction
from backend.domain.llm.multimodal import MultimodalImageBlock, MultimodalMessage, MultimodalTextBlock
from backend.infrastructure.db.models import FileModel, JDSourceAssetModel, JobDescriptionModel
from backend.infrastructure.extractors.jd_extractor import JDExtractionError, JDExtractor
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.parsers import get_parser
from backend.infrastructure.storage.minio_client import download_file
from backend.infrastructure.web.safe_fetcher import SafeWebFetcher, SafeWebFetchError


class VisionTranscriptPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: uuid.UUID
    order: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=100_000)
    warnings: list[str] = Field(default_factory=list, max_length=20)


class VisionTranscriptOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pages: list[VisionTranscriptPage] = Field(min_length=1, max_length=8)


class JDProcessingService:
    """Stateful worker operations guarded by a processing run UUID."""

    async def source_validate(self, session: AsyncSession, jd_id: uuid.UUID, run_id: uuid.UUID) -> str:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return "stale"
        if jd.source_type != JDSourceType.IMAGE.value:
            return "processing"
        assets = await self._ordered_assets(session, jd_id)
        if not assets:
            raise JDProcessingError("Image source is missing", code=1002)
        if not await self._write_current(
            session,
            jd_id,
            run_id,
            {
                "status": JDStatus.PROCESSING.value,
                "processing_step": JDProcessingStep.VISION_EXTRACT.value,
                "processing_error": None,
            },
        ):
            return "stale"
        return "processing"

    async def vision_extract(self, session: AsyncSession, jd_id: uuid.UUID, run_id: uuid.UUID) -> str:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return "stale"
        if jd.source_type != JDSourceType.IMAGE.value:
            return "processing"
        assets = await self._ordered_assets(session, jd_id)
        if not assets:
            raise JDProcessingError("Image source is missing", code=1002)
        if not await self._write_current(
            session,
            jd_id,
            run_id,
            {
                "status": JDStatus.PROCESSING.value,
                "processing_step": JDProcessingStep.VISION_EXTRACT.value,
                "processing_error": None,
            },
        ):
            return "stale"
        config = await get_active_verified_config(session)
        if config is None:
            await session.rollback()
            raise JDProcessingError("LLM not configured or not verified", code=428)
        messages = await self._build_vision_messages(session, assets)
        gateway = LLMGateway.from_config(config)
        await session.rollback()
        try:
            response = await gateway.complete_multimodal(
                messages,
                response_format={"type": "json_object", "schema": VisionTranscriptOutput.model_json_schema()},
            )
            parsed = _parse_vision_response(response.content)
        except (ValidationError, ValueError) as exc:
            raise JDProcessingError("JD Vision transcription failed", code=5001) from exc
        current = await self._current_jd(session, jd_id, run_id)
        if current is None:
            return "stale"
        by_id = {asset.id: asset for asset in assets}
        if {page.asset_id for page in parsed.pages} - set(by_id):
            raise JDProcessingError("JD Vision transcription referenced an unknown image", code=5001)
        ordered_pages = sorted(parsed.pages, key=lambda page: page.order)
        raw_text = normalize_jd_text("\n\n".join(page.text for page in ordered_pages))
        page_map = [page.model_dump(mode="json") for page in ordered_pages]
        visible_chars = len(re.sub(r"\s", "", raw_text))
        if visible_chars < 30 or len(raw_text) > 100_000:
            raise JDProcessingError("JD Vision transcription did not contain enough readable text", code=5001)
        for page in ordered_pages:
            asset = by_id[page.asset_id]
            asset.status = "ready"
            asset.transcript_blocks = [page.model_dump(mode="json")]
            asset.processing_error_code = None
        if not await self._write_current(
            session,
            jd_id,
            run_id,
            {
                "raw_text": raw_text,
                "parser_version": "jd-vision-v1",
                "vision_metadata": {
                    "provider": config.provider,
                    "model": response.model,
                    "transcriber_version": "jd-vision-v1",
                    "warnings": [warning for page in ordered_pages for warning in page.warnings],
                    "pages": page_map,
                },
                "processing_step": JDProcessingStep.TEXT_QUALITY_CHECK.value,
            },
        ):
            return "stale"
        return "processing"

    async def text_quality_check(self, session: AsyncSession, jd_id: uuid.UUID, run_id: uuid.UUID) -> str:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return "stale"
        if jd.source_type != JDSourceType.IMAGE.value:
            return "processing"
        normalized = normalize_jd_text(jd.raw_text)
        visible_chars = len(re.sub(r"\s", "", normalized))
        if visible_chars < 30 or len(normalized) > 100_000:
            raise JDProcessingError("Job description content is too short or too large to process")
        if not await self._write_current(
            session,
            jd_id,
            run_id,
            {"raw_text": normalized, "processing_step": JDProcessingStep.DUPLICATE_CHECK.value},
        ):
            return "stale"
        return "processing"

    async def source_extract(self, session: AsyncSession, jd_id: uuid.UUID, run_id: uuid.UUID) -> str:
        jd = await self._current_jd(session, jd_id, run_id)
        if jd is None:
            return "stale"
        if jd.source_type == JDSourceType.IMAGE.value:
            return "processing"
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
            JobDescriptionModel.user_id.is_(None) if jd.user_id is None else JobDescriptionModel.user_id == jd.user_id
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
        values["parser_version"] = extractor.version
        # The model name has no JD-table column; it travels inside the review
        # draft and lands in the published version's source_metadata.
        values["review_draft"] = draft_from_extraction(
            extraction,
            parser_version=extractor.version,
            model_name=extractor.model_info or None,
        ).model_dump(mode="json")
        values["review_revision"] = (current.review_revision or 0) + 1
        values.update(
            {
                "status": JDStatus.NEEDS_REVIEW.value,
                "processing_step": JDProcessingStep.REVIEW.value,
                "processing_error": None,
                "structured_revision": JobDescriptionModel.structured_revision + 1,
            }
        )
        if not await self._write_current(session, jd_id, run_id, values):
            return "stale"
        return JDStatus.NEEDS_REVIEW.value

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
        return merged_extraction_values(
            field_sources=jd.field_sources,
            extraction=extraction,
            overwrite_manual=overwrite_manual,
        )

    async def _read_source(self, session: AsyncSession, jd: JobDescriptionModel) -> tuple[str, str]:
        if jd.source_type == JDSourceType.IMAGE.value:
            return jd.raw_text, "jd-vision-v1"
        if jd.source_type == JDSourceType.TEXT.value:
            return jd.raw_text, "direct-text-v1"
        if jd.source_type == JDSourceType.URL.value:
            if not jd.source_url:
                raise JDProcessingError("URL source is missing")
            return await SafeWebFetcher().fetch_text(jd.source_url), "safe-web-v1"
        if jd.source_type not in {JDSourceType.FILE.value, JDSourceType.IMAGE.value} or jd.source_file_id is None:
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
        supported = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg"}
        if extension not in supported:
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

    async def _ordered_assets(self, session: AsyncSession, jd_id: uuid.UUID) -> list[JDSourceAssetModel]:
        result = await session.execute(
            select(JDSourceAssetModel).where(JDSourceAssetModel.jd_id == jd_id).order_by(JDSourceAssetModel.order_index)
        )
        return list(result.scalars().all())

    async def _build_vision_messages(
        self,
        session: AsyncSession,
        assets: list[JDSourceAssetModel],
    ) -> list[MultimodalMessage]:
        blocks: list[MultimodalTextBlock | MultimodalImageBlock] = [
            MultimodalTextBlock(
                text=(
                    "Transcribe the visible job description text from these screenshots in order. "
                    "Return JSON with pages: asset_id, order, text, warnings. Do not infer missing content."
                )
            )
        ]
        settings = get_settings()
        for asset in assets:
            file_record = await session.get(FileModel, asset.file_id) if asset.file_id else None
            if file_record is None:
                raise JDProcessingError("Image source is unavailable", code=1002)
            storage_path = file_record.storage_path
            await session.rollback()
            data = await asyncio.to_thread(download_file, settings.MINIO_BUCKET_RESUMES, storage_path)
            blocks.append(
                MultimodalImageBlock(
                    media_type=asset.media_type,  # type: ignore[arg-type]
                    data_base64=base64.b64encode(data).decode("ascii"),
                    asset_id=str(asset.id),
                )
            )
        return [MultimodalMessage(role="user", content=blocks)]

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


def _parse_vision_response(content: str) -> VisionTranscriptOutput:
    import json

    return VisionTranscriptOutput.model_validate(json.loads(content))


__all__ = ["JDProcessingError", "JDProcessingService", "VisionTranscriptOutput", "VisionTranscriptPage"]
