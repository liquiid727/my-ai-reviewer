"""简历上传服务 —— 负责文件校验、去重、对象存储上传和数据库记录创建。"""

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.resume.exceptions import (
    FileTooLargeError,
    UnsupportedFileFormatError,
)
from backend.infrastructure.db.models import FileModel, ResumeModel, ResumePrivacyManifestModel
from backend.infrastructure.privacy import QuarantineCipher
from backend.infrastructure.storage.minio_client import ensure_bucket, upload_file
from backend.tasks.resume_tasks import process_resume_pipeline

# 允许上传的文件扩展名
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".htm"}
# 文件大小上限：10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# 扩展名 → MIME 类型映射
CONTENT_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
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


@dataclass(frozen=True)
class PreparedQuarantinedUpload:
    safe_name: str
    object_name: str
    encrypted_data: bytes
    content_hash: str
    source_content_type: str


def prepare_quarantined_upload(
    *,
    resume_id: uuid.UUID,
    filename: str,
    file_data: bytes,
    encryption_key: str,
) -> PreparedQuarantinedUpload:
    """Encrypt a validated source and remove user-controlled filename data."""
    ext = _validate_file(filename, len(file_data))
    encrypted = QuarantineCipher(encryption_key).encrypt(file_data)
    return PreparedQuarantinedUpload(
        safe_name=f"resume{ext}",
        object_name=f"{resume_id}/{uuid.uuid4()}.enc",
        encrypted_data=encrypted,
        content_hash=_compute_sha256(encrypted),
        source_content_type=CONTENT_TYPE_MAP.get(ext, "application/octet-stream"),
    )


async def upload_resume(
    session: AsyncSession,
    filename: str,
    file_data: bytes,
    user_id: uuid.UUID | None = None,
) -> dict[str, str]:
    """上传简历的完整流程：校验 → 去重 → 存储 → 建记录 → 触发流水线。"""
    settings = get_settings()
    encryption_key = settings.PRIVACY_QUARANTINE_KEY or settings.ENCRYPTION_KEY
    if not encryption_key:
        raise RuntimeError("Privacy quarantine key is not configured")
    resume_id = uuid.uuid4()
    prepared = prepare_quarantined_upload(
        resume_id=resume_id,
        filename=filename,
        file_data=file_data,
        encryption_key=encryption_key,
    )

    ensure_bucket(settings.MINIO_BUCKET_QUARANTINE)
    upload_file(
        bucket=settings.MINIO_BUCKET_QUARANTINE,
        object_name=prepared.object_name,
        data=prepared.encrypted_data,
        content_type="application/octet-stream",
    )

    owner_id = user_id or resume_id
    file_record = FileModel(
        original_name=prepared.safe_name,
        storage_path=prepared.object_name,
        content_type=prepared.source_content_type,
        size_bytes=len(prepared.encrypted_data),
        sha256_hash=prepared.content_hash,
        owner_type="resume",
        owner_id=owner_id,
    )
    session.add(file_record)
    await session.flush()

    resume_record = ResumeModel(
        id=resume_id,
        user_id=user_id,
        file_id=file_record.id,
        status="uploaded",
    )
    session.add(resume_record)
    session.add(ResumePrivacyManifestModel(
        resume_id=resume_id,
        status="scanning",
        quarantine_path=prepared.object_name,
        quarantine_expires_at=datetime.now(timezone.utc) + timedelta(
            seconds=settings.PRIVACY_QUARANTINE_TTL_SECONDS,
        ),
    ))
    await session.flush()
    await session.commit()

    # ── 异步触发简历处理流水线（Celery） ──
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, process_resume_pipeline, str(resume_record.id))

    return {
        "resume_id": str(resume_record.id),
        "status": resume_record.status,
    }
