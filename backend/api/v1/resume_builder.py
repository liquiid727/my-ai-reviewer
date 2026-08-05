"""简历制作 API 端点 —— 草稿 CRUD、AI 润色、证件照、分页预览与 PDF 导出。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application import llm_config_service as llm_config_service
from backend.application import resume_edit_service as resume_edit_service
from backend.config import get_settings
from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder import services as services
from backend.domain.resume_builder.editing import DraftRevisionConflictError
from backend.domain.resume_builder.enums import LayoutDensity, TemplateId
from backend.domain.resume_builder.reference_templates import list_reference_templates
from backend.domain.resume_builder.schemas import ExportOptions, LayoutPolicy
from backend.infrastructure.cache.redis_cache import (
    cache_get_bytes,
    cache_get_json,
    cache_set_bytes,
    cache_set_json,
)
from backend.infrastructure.db.database import get_db
from backend.infrastructure.imaging import (
    BG_COLORS,
    FaceNotFoundError,
    ImageDecodeError,
    ImagingNotAvailableError,
    process_photo,
)
from backend.infrastructure.llm.gateway import LLMGateway as LLMGateway
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
LLM_NOT_READY_CODE = 428
LLM_NOT_READY_MESSAGE = "LLM not configured or not verified"

# GET preview 输出仅由 (draft, revision) 决定：内容/模板/设计令牌/分页策略任一变化
# 都会使 revision +1，且缓存的预览 PDF 只含 masked 内容（不含真实 PII），
# 因此可按 revision 复用已渲染 PDF，避免重复 Playwright 渲染。
_PREVIEW_CACHE_TTL_SECONDS = 6 * 3600
# 单飞锁：同一 revision 的并发预览请求只触发一次渲染
_preview_render_locks: dict[str, asyncio.Lock] = {}


def _preview_response(pdf_bytes: bytes, meta: dict[str, Any]) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=resume-preview.pdf",
            "X-Page-Count": str(meta["page_count"]),
            "X-Target-Met": "true" if meta["target_met"] else "false",
            "X-Layout-Density": meta["applied_density"],
            "Cache-Control": "no-store",
        },
    )


# ─────────────────────────── 请求体模型 ───────────────────────────


class UpdateDraftRequest(BaseModel):
    """更新草稿的请求体（所有字段可选，按需更新）。"""

    title: str | None = None
    identity: dict[str, Any] | None = None
    summary: str | None = None
    sections: list[dict[str, Any]] | None = None
    template_id: TemplateId | None = None
    design_tokens: dict[str, Any] | None = None
    layout_policy: LayoutPolicy | None = None
    base_revision: int | None = Field(default=None, ge=1)


class PolishSectionRequest(BaseModel):
    """润色某区块要点的请求体。"""

    section_type: ResumeSectionType
    items: list[str]
    context: str | None = None


class ExportRequest(BaseModel):
    """导出 PDF 的请求体。"""

    template_id: TemplateId | None = None
    layout_policy: LayoutPolicy | None = None
    persist: bool = False
    replacements: dict[str, str] = Field(default_factory=dict)
    photo_data_uri: str | None = None


class ConfirmPhotoRequest(BaseModel):
    """确认采用处理后证件照的请求体。"""

    object_name: str


class DraftOrderRequest(BaseModel):
    """草稿列表的完整排序结果。"""

    draft_ids: list[uuid.UUID]


class AssistantTurnRequest(BaseModel):
    """发送一条助手指令并生成结构化提案。"""

    message: str = Field(min_length=1, max_length=4000)
    base_revision: int = Field(ge=1)
    client_request_id: str = Field(min_length=8, max_length=100)
    conversation_id: uuid.UUID | None = None


class ApplyProposalRequest(BaseModel):
    base_revision: int = Field(ge=1)
    selected_operation_ids: list[str] = Field(min_length=1, max_length=30)


# ─────────────────────────── 序列化 ───────────────────────────


def _serialize_draft(model: Any) -> dict[str, Any]:
    """把草稿模型序列化为前端可用的 dict。"""
    draft = services.draft_model_to_schema(model)
    return {
        "draft_id": str(model.id),
        "resume_id": str(model.resume_id) if model.resume_id else None,
        "title": model.title,
        "template_id": model.template_id,
        "layout_policy": draft.layout_policy.model_dump(mode="json"),
        "status": model.status,
        "revision": int(getattr(model, "revision", 1)),
        "identity": draft.identity,
        "summary": draft.summary,
        "sections": [s.model_dump(mode="json") for s in draft.sections],
        "design_tokens": draft.design_tokens.model_dump(mode="json"),
        "privacy_placeholders": (model.privacy_manifest or {}).get("placeholders", []),
    }


# ─────────────────────────── 端点 ───────────────────────────


@router.get("/templates")
async def list_templates() -> APIResponse:
    """返回可选模板与密度档位。"""
    return APIResponse(
        data={
            "templates": [{"id": t.value} for t in TemplateId],
            "densities": [{"id": d.value} for d in LayoutDensity],
        }
    )


@router.get("/reference-templates")
async def list_reference_template_options() -> APIResponse:
    """返回内置参考简历模板列表（供用户一键创建可编辑草稿）。"""
    return APIResponse(
        data=[
            {
                "key": t.key,
                "name": t.name,
                "description": t.description,
                "tags": list(t.tags),
            }
            for t in list_reference_templates()
        ]
    )


@router.get("/drafts")
async def list_drafts(session: AsyncSession = Depends(get_db)) -> APIResponse:
    """返回全部简历草稿概要，按用户维护的顺序（供简历列表页展示）。"""
    models = await services.list_drafts(session)
    return APIResponse(
        data=[
            {
                "draft_id": str(m.id),
                "resume_id": str(m.resume_id) if m.resume_id else None,
                "title": m.title,
                "template_id": m.template_id,
                "status": m.status,
                "sort_order": m.sort_order,
                "overall_score": (m.latest_score or {}).get("overall_score"),
                "scored_at": m.scored_at.isoformat() if m.scored_at else None,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat(),
            }
            for m in models
        ]
    )


@router.put("/drafts/order")
async def reorder_drafts(
    body: DraftOrderRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """持久化简历草稿卡片顺序。"""
    try:
        models = await services.reorder_drafts(session, body.draft_ids)
    except ValueError as exc:
        return APIResponse(code=400, message=str(exc))
    return APIResponse(
        data=[
            {
                "draft_id": str(m.id),
                "resume_id": str(m.resume_id) if m.resume_id else None,
                "title": m.title,
                "template_id": m.template_id,
                "status": m.status,
                "sort_order": m.sort_order,
                "overall_score": (m.latest_score or {}).get("overall_score"),
                "scored_at": m.scored_at.isoformat() if m.scored_at else None,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat(),
            }
            for m in models
        ]
    )


@router.post("/from-reference/{template_key}")
async def create_from_reference(
    template_key: str,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """从内置参考模板创建独立草稿，返回 draft_id。"""
    try:
        model = await services.create_draft_from_reference(session, template_key)
    except ValueError:
        return APIResponse(code=404, message="Reference template not found")
    return APIResponse(data={"draft_id": str(model.id)})


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
    patch = body.model_dump(exclude_unset=True, exclude={"base_revision"})
    try:
        model = await services.update_draft(
            session,
            draft_id,
            patch,
            expected_revision=body.base_revision,
        )
    except DraftRevisionConflictError as exc:
        _raise_revision_conflict(exc)
    return APIResponse(data=_serialize_draft(model))


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """删除草稿及其导出记录。"""
    try:
        await services.delete_draft(session, draft_id)
    except ValueError:
        return APIResponse(code=404, message="Resume draft not found")
    return APIResponse(message="Resume draft deleted", data={"draft_id": str(draft_id)})


async def _get_builder_llm_gateway(session: AsyncSession) -> LLMGateway | None:
    """从已验证的持久化配置创建 Builder 网关，未就绪时返回 None。"""
    config = await llm_config_service.get_active_verified_config(session)
    if config is None:
        return None
    return LLMGateway.from_config(config)


@router.get("/{draft_id}/assistant")
async def get_assistant_conversation(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """返回草稿最近一次 AI 编辑会话。"""
    await services.get_draft(session, draft_id)
    conversation = await resume_edit_service.get_latest_conversation(session, draft_id=draft_id)
    return APIResponse(data=conversation)


@router.post("/{draft_id}/assistant/turns")
async def create_assistant_turn(
    draft_id: uuid.UUID,
    body: AssistantTurnRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """生成提案；此端点不会修改草稿。"""
    config = await llm_config_service.get_active_verified_config(session)
    if config is None:
        return APIResponse(code=LLM_NOT_READY_CODE, message=LLM_NOT_READY_MESSAGE)
    try:
        conversation = await resume_edit_service.propose_edit(
            session,
            draft_id=draft_id,
            base_revision=body.base_revision,
            instruction=body.message.strip(),
            client_request_id=body.client_request_id,
            conversation_id=body.conversation_id,
            llm_config=config,
        )
    except DraftRevisionConflictError as exc:
        _raise_revision_conflict(exc)
    return APIResponse(data=conversation)


@router.post("/{draft_id}/assistant/proposals/{proposal_id}/apply")
async def apply_assistant_proposal(
    draft_id: uuid.UUID,
    proposal_id: uuid.UUID,
    body: ApplyProposalRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """原子应用用户选中的提案操作。"""
    try:
        model = await resume_edit_service.apply_proposal(
            session,
            draft_id=draft_id,
            proposal_id=proposal_id,
            base_revision=body.base_revision,
            selected_operation_ids=set(body.selected_operation_ids),
        )
    except DraftRevisionConflictError as exc:
        _raise_revision_conflict(exc)
    except resume_edit_service.ProposalStateError as exc:
        raise HTTPException(status_code=409, detail={"code": "PROPOSAL_STATE_CONFLICT", "message": str(exc)})
    return APIResponse(data=_serialize_draft(model))


@router.post("/{draft_id}/assistant/proposals/{proposal_id}/reject")
async def reject_assistant_proposal(
    draft_id: uuid.UUID,
    proposal_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """拒绝未应用的提案，不修改草稿。"""
    try:
        proposal = await resume_edit_service.reject_proposal(
            session,
            draft_id=draft_id,
            proposal_id=proposal_id,
        )
    except resume_edit_service.ProposalStateError as exc:
        raise HTTPException(status_code=409, detail={"code": "PROPOSAL_STATE_CONFLICT", "message": str(exc)})
    return APIResponse(data={"proposal_id": str(proposal.id), "status": proposal.status})


@router.post("/{draft_id}/assistant/proposals/{proposal_id}/undo")
async def undo_assistant_proposal(
    draft_id: uuid.UUID,
    proposal_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """撤销仍处于当前版本的已应用提案。"""
    try:
        model = await resume_edit_service.undo_proposal(
            session,
            draft_id=draft_id,
            proposal_id=proposal_id,
        )
    except DraftRevisionConflictError as exc:
        _raise_revision_conflict(exc)
    except resume_edit_service.ProposalStateError as exc:
        raise HTTPException(status_code=409, detail={"code": "PROPOSAL_STATE_CONFLICT", "message": str(exc)})
    return APIResponse(data=_serialize_draft(model))


def _raise_revision_conflict(exc: DraftRevisionConflictError) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "code": "DRAFT_REVISION_CONFLICT",
            "expected_revision": exc.expected,
            "actual_revision": exc.actual,
        },
    )


@router.post("/{draft_id}/polish")
async def polish_section(
    draft_id: uuid.UUID,
    body: PolishSectionRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """对指定区块的要点返回 AI 润色建议（保留原文，供前端逐条接受）。"""
    await services.get_draft(session, draft_id)  # 校验草稿存在
    gateway = await _get_builder_llm_gateway(session)
    if gateway is None:
        return APIResponse(code=LLM_NOT_READY_CODE, message=LLM_NOT_READY_MESSAGE)
    result = await services.polish_draft_section(
        gateway,
        body.section_type,
        body.items,
        body.context,
    )
    return APIResponse(data=result.model_dump(mode="json"))


@router.post("/{draft_id}/score")
async def score_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """复用 9 维评估器对草稿打分，并把最新评分持久化到草稿。"""
    model = await services.get_draft(session, draft_id)
    gateway = await _get_builder_llm_gateway(session)
    if gateway is None:
        return APIResponse(code=LLM_NOT_READY_CODE, message=LLM_NOT_READY_MESSAGE)
    draft = services.draft_model_to_schema(model)
    evaluation = await services.score_draft(gateway, draft)
    # 元信息（模型/token 用量）不落库，仅用于服务端日志追溯
    evaluation.pop("_meta", None)
    model = await services.save_draft_score(session, draft_id, evaluation)
    return APIResponse(data=services.serialize_draft_score(model))


@router.get("/{draft_id}/score")
async def get_draft_score(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """返回草稿最近一次持久化的评分结果；未评分时 data 为 null。"""
    model = await services.get_draft(session, draft_id)
    return APIResponse(data=services.serialize_draft_score(model))


@router.get("/{draft_id}/preview")
async def preview_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """返回与导出完全相同的分页 PDF（供 iframe 预览）；同一 revision 复用渲染缓存。"""
    model = await services.get_draft(session, draft_id)
    revision = int(getattr(model, "revision", 0))
    cache_prefix = f"builder:preview:{draft_id}:r{revision}"
    pdf_key = f"{cache_prefix}:pdf"
    meta_key = f"{cache_prefix}:meta"

    cached_pdf = await cache_get_bytes(pdf_key)
    cached_meta = await cache_get_json(meta_key)
    if cached_pdf is not None and cached_meta is not None:
        return _preview_response(cached_pdf, cached_meta)

    lock = _preview_render_locks.setdefault(cache_prefix, asyncio.Lock())
    async with lock:
        # 双检：等待锁期间其他请求可能已完成渲染并写入缓存
        cached_pdf = await cache_get_bytes(pdf_key)
        cached_meta = await cache_get_json(meta_key)
        if cached_pdf is not None and cached_meta is not None:
            return _preview_response(cached_pdf, cached_meta)
        pdf_bytes, result = await services.export_draft_pdf(session, model, ExportOptions())
        meta = {
            "page_count": result.page_count,
            "target_met": result.target_met,
            "applied_density": result.applied_density.value,
        }
        await cache_set_bytes(pdf_key, pdf_bytes, _PREVIEW_CACHE_TTL_SECONDS)
        await cache_set_json(meta_key, meta, _PREVIEW_CACHE_TTL_SECONDS)
        return _preview_response(pdf_bytes, meta)


@router.post("/{draft_id}/preview")
async def preview_draft_with_replacements(
    draft_id: uuid.UUID,
    body: ExportRequest,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Render a no-store preview with replacements held only for this request."""
    model = await services.get_draft(session, draft_id)
    options = ExportOptions(
        template_id=body.template_id,
        layout_policy=body.layout_policy,
        persist=False,
        replacements=body.replacements,
    )
    if body.photo_data_uri:
        pdf_bytes, result = await services.export_draft_pdf(
            session,
            model,
            options,
            photo_data_uri=body.photo_data_uri,
        )
    else:
        pdf_bytes, result = await services.export_draft_pdf(session, model, options)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=resume-preview.pdf",
            "X-Page-Count": str(result.page_count),
            "X-Target-Met": "true" if result.target_met else "false",
            "X-Layout-Density": result.applied_density.value,
            "Cache-Control": "no-store",
        },
    )


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
        layout_policy=body.layout_policy,
        persist=False,
        replacements=body.replacements,
    )
    if body.photo_data_uri:
        pdf_bytes, result = await services.export_draft_pdf(
            session,
            model,
            options,
            photo_data_uri=body.photo_data_uri,
        )
    else:
        pdf_bytes, result = await services.export_draft_pdf(session, model, options)
    # 非 ASCII 标题用 RFC 5987 编码，避免响应头 latin-1 编码失败；filename= 提供 ASCII 回退
    filename = f"{model.title or 'resume'}.pdf"
    disposition = f"attachment; filename=\"resume.pdf\"; filename*=UTF-8''{quote(filename, safe='')}"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": disposition,
            "X-Page-Count": str(result.page_count),
            "X-Target-Met": "true" if result.target_met else "false",
            "X-Layout-Density": result.applied_density.value,
            "Cache-Control": "no-store",
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

    return APIResponse(
        data={
            "original_object": original_object,
            "processed_object": processed_object,
            "original_url": original_url,
            "processed_url": processed_url,
            "background_replaced": result.background_replaced,
            "degraded_reason": result.degraded_reason,
            "bg_color": bg_color,
        }
    )


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
