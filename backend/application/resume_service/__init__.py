"""简历上传服务 —— 负责文件校验、去重、对象存储上传和数据库记录创建。"""

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
import asyncio

from backend.tasks.resume_tasks import process_resume_pipeline

# 允许上传的文件扩展名
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
# 文件大小上限：10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# 扩展名 → MIME 类型映射
CONTENT_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def _validate_file(filename: str, size: int) -> str:
    """校验文件格式和大小，返回小写扩展名。"""
    ext = PurePosixPath(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileFormatError(ext)
    if size > MAX_FILE_SIZE:
        raise FileTooLargeError(size, MAX_FILE_SIZE)
    return ext


def _compute_sha256(data: bytes) -> str:
    """计算文件内容的 SHA-256 哈希值，用于去重检测。"""
    return hashlib.sha256(data).hexdigest()


async def upload_resume(
    session: AsyncSession,
    filename: str,
    file_data: bytes,
    user_id: uuid.UUID | None = None,
) -> dict[str, str]:
    """上传简历的完整流程：校验 → 去重 → 存储 → 建记录 → 触发流水线。"""
    ext = _validate_file(filename, len(file_data))
    sha256_hash = _compute_sha256(file_data)

    # ── 去重检测：如果相同文件已上传过，直接返回已有记录 ──
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

    # ── 上传文件到 MinIO 对象存储 ──
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

    # ── 创建文件记录和简历记录 ──
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

    # ── 异步触发简历处理流水线（Celery） ──
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, process_resume_pipeline, str(resume_record.id))

    return {
        "resume_id": str(resume_record.id),
        "file_id": str(file_record.id),
        "status": resume_record.status,
    }
