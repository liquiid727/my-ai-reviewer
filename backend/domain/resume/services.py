import os
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.resume.enums import ResumeStatus
from backend.infrastructure.db.models import FileModel, ResumeModel
from backend.infrastructure.parsers import get_parser
from backend.infrastructure.storage.minio_client import download_file


async def extract_text(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel:
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    file_record = await session.get(FileModel, resume.file_id)
    if file_record is None:
        raise ValueError(f"File not found for resume: {resume_id}")

    settings = get_settings()
    ext = Path(file_record.original_name).suffix

    tmp_path: str | None = None
    try:
        file_bytes = download_file(settings.MINIO_BUCKET_RESUMES, file_record.storage_path)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        parser = get_parser(ext)
        result = parser.parse(tmp_path)

        if not result.raw_text.strip():
            resume.status = ResumeStatus.FAILED
            resume.parse_error = "Parsed document contains no text"
            resume.parser_version = parser.version
            await session.commit()
            return resume

        resume.raw_text = result.raw_text
        resume.parser_version = parser.version
        resume.parse_error = None
        resume.status = ResumeStatus.TEXT_PARSED
        await session.commit()

    except Exception as exc:
        resume.status = ResumeStatus.FAILED
        resume.parse_error = str(exc)
        await session.commit()
        raise

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return resume
