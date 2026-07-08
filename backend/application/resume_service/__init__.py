import hashlib
import uuid
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.resume.exceptions import (
    FileTooLargeError,
    UnsupportedFileFormatError,
)
from backend.infrastructure.db.models import FileModel, ResumeModel
from backend.infrastructure.storage.minio_client import upload_file

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

CONTENT_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def _validate_file(filename: str, size: int) -> str:
    ext = PurePosixPath(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileFormatError(ext)
    if size > MAX_FILE_SIZE:
        raise FileTooLargeError(size, MAX_FILE_SIZE)
    return ext


def _compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def upload_resume(
    session: AsyncSession,
    filename: str,
    file_data: bytes,
    user_id: uuid.UUID | None = None,
) -> dict[str, str]:
    ext = _validate_file(filename, len(file_data))
    sha256_hash = _compute_sha256(file_data)

    stmt = select(FileModel).where(FileModel.sha256_hash == sha256_hash)
    result = await session.execute(stmt)
    existing_file = result.scalar_one_or_none()

    if existing_file is not None:
        resume_stmt = select(ResumeModel).where(ResumeModel.file_id == existing_file.id)
        resume_result = await session.execute(resume_stmt)
        existing_resume = resume_result.scalar_one_or_none()
        if existing_resume is not None:
            return {
                "resume_id": str(existing_resume.id),
                "file_id": str(existing_file.id),
                "status": str(existing_resume.status),
            }

    settings = get_settings()
    owner_id = user_id or uuid.uuid4()
    object_name = f"{owner_id}/{uuid.uuid4()}{ext}"
    content_type = CONTENT_TYPE_MAP.get(ext, "application/octet-stream")

    upload_file(
        bucket=settings.MINIO_BUCKET_RESUMES,
        object_name=object_name,
        data=file_data,
        content_type=content_type,
    )

    file_record = FileModel(
        original_name=filename,
        storage_path=object_name,
        content_type=content_type,
        size_bytes=len(file_data),
        sha256_hash=sha256_hash,
        owner_type="resume",
        owner_id=owner_id,
    )
    session.add(file_record)
    await session.flush()

    resume_record = ResumeModel(
        user_id=user_id,
        file_id=file_record.id,
        status="uploaded",
    )
    session.add(resume_record)
    await session.flush()
    await session.commit()

    return {
        "resume_id": str(resume_record.id),
        "file_id": str(file_record.id),
        "status": resume_record.status,
    }
