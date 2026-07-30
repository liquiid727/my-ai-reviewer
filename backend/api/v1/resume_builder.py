"""简历制作 API 端点 —— 草稿 CRUD、AI 润色、AI 打分、证件照处理、HTML 预览与 PDF 导出。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.config import get_settings
from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder import services
from backend.domain.resume_builder.enums import LayoutDensity, TemplateId
from backend.domain.resume_builder.schemas import ExportOptions
from backend.infrastructure.db.database import get_db
from backend.infrastructure.imaging import (
    BG_COLORS,
    FaceNotFoundError,
    ImageDecodeError,
    ImagingNotAvailableError,
    process_photo,
)
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.storage.minio_client import (
    ensure_bucket,
    object_exists,
    presigned_url,
    upload_file,
)

router = APIRouter(prefix="/builder", tags=["builder"])

# 证件照上传限制：仅 jpg/png，最大 10MB
PHOTO_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
PHOTO_MAX_SIZE = 10 * 1024 * 1024


# ─────────────────────────── 请求体模型 ───────────────────────────


class UpdateDraftRequest(BaseModel):
    """更新草稿的请求体（所有字段可选，按需更新）。"""
    title: str | None = None
    identity: dict[str, Any] | None = None
    summary: str | None = None
    sections: list[dict[str, Any]] | None = None
    template_id: TemplateId | None = None
    design_tokens: dict[str, Any] | None = None
    auto_one_page: bool | None = None


class PolishSectionRequest(BaseModel):
    """润色某区块要点的请求体。"""
    section_type: ResumeSectionType
    items: list[str]
    context: str | None = None


class ExportRequest(BaseModel):
    """导出 PDF 的请求体。"""
    template_id: TemplateId | None = None
    auto_one_page: bool = False
    persist: bool = False


class ConfirmPhotoRequest(BaseModel):
    """确认采用处理后证件照的请求体。"""
    object_name: str


# ─────────────────────────── 序列化 ───────────────────────────


def _serialize_draft(model: Any) -> dict[str, Any]:
    """把草稿模型序列化为前端可用的 dict。"""
    draft = services.draft_model_to_schema(model)
    return {
        "draft_id": str(model.id),
        "resume_id": str(model.resume_id) if model.resume_id else None,
        "title": model.title,
        "template_id": model.template_id,
        "auto_one_page": model.auto_one_page,
        "status": model.status,
        "identity": draft.identity,
        "summary": draft.summary,
        "sections": [s.model_dump(mode="json") for s in draft.sections],
        "design_tokens": draft.design_tokens.model_dump(mode="json"),
    }


# ─────────────────────────── 端点 ───────────────────────────


@router.get("/templates")
async def list_templates() -> APIResponse:
    """返回可选模板与密度档位。"""
    return APIResponse(data={
        "templates": [{"id": t.value} for t in TemplateId],
        "densities": [{"id": d.value} for d in LayoutDensity],
    })


@router.post("/from-resume/{resume_id}")
async def create_from_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """从已解析简历创建草稿，返回 draft_id。"""
    model = await services.create_draft_from_profile(session, resume_id)
    return APIResponse(data={"draft_id": str(model.id)})


@router.get("/{draft_id}")
async def get_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取草稿详情。"""
    model = await services.get_draft(session, draft_id)
    return APIResponse(data=_serialize_draft(model))


@router.put("/{draft_id}")
async def update_draft(
    draft_id: uuid.UUID,
    body: UpdateDraftRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新草稿的内容 / 模板 / 设计令牌。"""
    patch = body.model_dump(exclude_unset=True)
    model = await services.update_draft(session, draft_id, patch)
    return APIResponse(data=_serialize_draft(model))


@router.post("/{draft_id}/polish")
async def polish_section(
    draft_id: uuid.UUID,
    body: PolishSectionRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """对指定区块的要点返回 AI 润色建议（保留原文，供前端逐条接受）。"""
    await services.get_draft(session, draft_id)  # 校验草稿存在
    gateway = LLMGateway.from_settings()
    result = await services.polish_draft_section(
        gateway, body.section_type, body.items, body.context,
    )
    return APIResponse(data=result.model_dump(mode="json"))


@router.post("/{draft_id}/score")
async def score_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """复用 9 维评估器对草稿打分。"""
    model = await services.get_draft(session, draft_id)
    draft = services.draft_model_to_schema(model)
    gateway = LLMGateway.from_settings()
    evaluation = await services.score_draft(gateway, draft)
    return APIResponse(data=evaluation)


@router.get("/{draft_id}/preview")
async def preview_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """返回渲染后的 HTML（供 iframe 预览）。"""
    model = await services.get_draft(session, draft_id)
    draft = services.draft_model_to_schema(model)
    html = services.render_draft_html(draft)
    return HTMLResponse(content=html)


@router.post("/{draft_id}/export")
async def export_draft(
    draft_id: uuid.UUID,
    body: ExportRequest,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """导出 PDF，直接返回文件流（可选持久化到对象存储）。"""
    model = await services.get_draft(session, draft_id)
    options = ExportOptions(
        template_id=body.template_id,
        auto_one_page=body.auto_one_page,
        persist=body.persist,
    )
    pdf_bytes, result = await services.export_draft_pdf(session, model, options)
    filename = f"{model.title or 'resume'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Page-Count": str(result.page_count),
            "X-Overflow": "true" if result.overflow else "false",
        },
    )


# ─────────────────────────── 证件照 ───────────────────────────


@router.post("/{draft_id}/photo")
async def upload_photo(
    draft_id: uuid.UUID,
    file: UploadFile,
    bg_color: str = "white",
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """上传生活照并处理为证件照，返回原图/结果预览（不写入草稿，需 confirm）。"""
    await services.get_draft(session, draft_id)  # 校验草稿存在

    if bg_color not in BG_COLORS:
        raise HTTPException(status_code=400, detail="INVALID_PHOTO")
    if file.content_type not in PHOTO_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="INVALID_PHOTO")
    # 先按声明尺寸拦截，再限额读取，避免超大请求体全量进内存
    if file.size is not None and file.size > PHOTO_MAX_SIZE:
        raise HTTPException(status_code=400, detail="INVALID_PHOTO")
    data = await file.read(PHOTO_MAX_SIZE + 1)
    if len(data) > PHOTO_MAX_SIZE:
        raise HTTPException(status_code=400, detail="INVALID_PHOTO")

    try:
        # rembg/人脸检测为 CPU 重操作，放线程池避免阻塞事件循环
        result = await asyncio.to_thread(process_photo, data, bg_color)
    except ImagingNotAvailableError as exc:
        raise HTTPException(status_code=501, detail="IMAGING_NOT_AVAILABLE") from exc
    except FaceNotFoundError as exc:
        raise HTTPException(status_code=422, detail="FACE_NOT_FOUND") from exc
    except ImageDecodeError as exc:
        raise HTTPException(status_code=400, detail="PHOTO_DECODE_FAILED") from exc

    # 原图与结果分别落 MinIO（可追溯）；对象名以 draft_id 为前缀供 confirm 归属校验
    settings = get_settings()
    bucket = settings.MINIO_BUCKET_PHOTOS
    uid = uuid.uuid4().hex[:8]
    original_ext = "png" if file.content_type == "image/png" else "jpg"
    original_object = f"{draft_id}/original-{uid}.{original_ext}"
    processed_object = f"{draft_id}/processed-{uid}.png"

    def _store_photo() -> tuple[str, str]:
        """MinIO SDK 为同步网络 I/O，打包进线程池避免阻塞事件循环。"""
        ensure_bucket(bucket)
        upload_file(bucket, original_object, data, file.content_type or "image/jpeg")
        upload_file(bucket, processed_object, result.png_bytes, "image/png")
        return presigned_url(bucket, original_object), presigned_url(bucket, processed_object)

    original_url, processed_url = await asyncio.to_thread(_store_photo)

    return APIResponse(data={
        "original_object": original_object,
        "processed_object": processed_object,
        "original_url": original_url,
        "processed_url": processed_url,
        "background_replaced": result.background_replaced,
        "degraded_reason": result.degraded_reason,
        "bg_color": bg_color,
    })


@router.put("/{draft_id}/photo/confirm")
async def confirm_photo(
    draft_id: uuid.UUID,
    body: ConfirmPhotoRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """确认采用处理后的证件照，写入草稿 identity.photo。"""
    # 归属校验：对象必须是该草稿产出的处理结果
    if not body.object_name.startswith(f"{draft_id}/processed-"):
        raise HTTPException(status_code=400, detail="PHOTO_NOT_OWNED")
    # 存在性校验：拒绝伪造的对象名，避免写入悬空引用
    settings = get_settings()
    exists = await asyncio.to_thread(object_exists, settings.MINIO_BUCKET_PHOTOS, body.object_name)
    if not exists:
        raise HTTPException(status_code=400, detail="PHOTO_NOT_OWNED")
    model = await services.set_draft_photo(session, draft_id, body.object_name)
    return APIResponse(data=_serialize_draft(model))


@router.delete("/{draft_id}/photo")
async def delete_photo(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """移除草稿的证件照引用（MinIO 对象保留可追溯）。"""
    model = await services.set_draft_photo(session, draft_id, None)
    return APIResponse(data=_serialize_draft(model))
