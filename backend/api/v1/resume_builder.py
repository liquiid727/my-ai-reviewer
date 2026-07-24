"""简历制作 API 端点 —— 草稿 CRUD、AI 润色、AI 打分、HTML 预览与 PDF 导出。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder import services
from backend.domain.resume_builder.enums import LayoutDensity, TemplateId
from backend.domain.resume_builder.schemas import ExportOptions
from backend.infrastructure.db.database import get_db
from backend.infrastructure.llm.gateway import LLMGateway

router = APIRouter(prefix="/builder", tags=["builder"])


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
