"""简历制作领域服务 —— 草稿创建/更新、AI 润色、AI 打分、PDF 导出。"""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.enums import TemplateId
from backend.domain.resume_builder.schemas import (
    DesignTokens,
    DraftItem,
    DraftSection,
    ExportOptions,
    ExportResult,
    PolishResult,
    ResumeDraft,
)
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    ResumeDraftModel,
    ResumeExportModel,
)
from backend.infrastructure.evaluators.llm_evaluator import LLMResumeEvaluator
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.polishers.llm_polisher import LLMResumePolisher
from backend.infrastructure.rendering.html_renderer import HtmlRenderer
from backend.infrastructure.rendering.pdf_renderer import PdfRenderer
from backend.infrastructure.storage.minio_client import (
    download_file,
    ensure_bucket,
    upload_file,
)

logger = logging.getLogger(__name__)

# ─────────────────────────── profile → draft 映射 ───────────────────────────


def _join_date(start: Any, end: Any) -> str | None:
    """把 start/end 拼成 "start ~ end" 形式的时间范围。"""
    start_s = str(start).strip() if start else ""
    end_s = str(end).strip() if end else ""
    if start_s and end_s:
        return f"{start_s} ~ {end_s}"
    return start_s or end_s or None


def _work_section(work_experiences: list[dict[str, Any]]) -> DraftSection:
    items: list[DraftItem] = []
    for w in work_experiences:
        bullets = [b for b in (w.get("responsibilities") or []) if b]
        bullets += [b for b in (w.get("achievements") or []) if b]
        items.append(DraftItem(
            heading=w.get("company"),
            subheading=w.get("title"),
            date_range=_join_date(w.get("start_date"), w.get("end_date")),
            bullets=bullets,
        ))
    return DraftSection(
        section_type=ResumeSectionType.WORK_EXPERIENCE,
        title="工作经历", items=items, order=1,
    )


def _project_section(projects: list[dict[str, Any]]) -> DraftSection:
    items: list[DraftItem] = []
    for p in projects:
        bullets: list[str] = []
        if p.get("responsibility"):
            bullets.append(str(p["responsibility"]))
        bullets += [b for b in (p.get("highlights") or []) if b]
        bullets += [b for b in (p.get("difficulties") or []) if b]
        bullets += [b for b in (p.get("metrics") or []) if b]
        items.append(DraftItem(
            heading=p.get("name"),
            subheading=p.get("role"),
            bullets=bullets,
        ))
    return DraftSection(
        section_type=ResumeSectionType.PROJECT_EXPERIENCE,
        title="项目经历", items=items, order=2,
    )


def _education_section(education: list[dict[str, Any]]) -> DraftSection:
    items: list[DraftItem] = []
    for e in education:
        degree_major = " ".join(x for x in [e.get("degree"), e.get("major")] if x)
        bullets = [f"GPA: {e['gpa']}"] if e.get("gpa") else []
        items.append(DraftItem(
            heading=e.get("school"),
            subheading=degree_major or None,
            date_range=_join_date(e.get("start_date"), e.get("end_date")),
            bullets=bullets,
        ))
    return DraftSection(
        section_type=ResumeSectionType.EDUCATION,
        title="教育背景", items=items, order=3,
    )


def _skills_section(skills: list[dict[str, Any]]) -> DraftSection:
    """按分类聚合技能名，每个分类一条 bullet。"""
    grouped: dict[str, list[str]] = {}
    for s in skills:
        name = s.get("name")
        if not name:
            continue
        category = s.get("category") or "other"
        grouped.setdefault(category, []).append(str(name))
    bullets = [f"{cat}: {', '.join(names)}" for cat, names in grouped.items()]
    return DraftSection(
        section_type=ResumeSectionType.SKILLS,
        title="技能", items=[DraftItem(bullets=bullets)] if bullets else [], order=4,
    )


def _certificates_section(certificates: list[dict[str, Any]]) -> DraftSection:
    bullets: list[str] = []
    for c in certificates:
        name = c.get("name")
        if not name:
            continue
        issuer = c.get("issuer")
        bullets.append(f"{name}（{issuer}）" if issuer else str(name))
    return DraftSection(
        section_type=ResumeSectionType.CERTIFICATES,
        title="证书", items=[DraftItem(bullets=bullets)] if bullets else [], order=5,
    )


def profile_to_draft(profile: CandidateProfileModel) -> ResumeDraft:
    """把候选人画像映射为可编辑草稿（bullet 化，默认 classic + normal）。"""
    identity = dict(profile.identity or {})
    summary_parts = [str(t) for t in (profile.ability_tags or [])]
    summary = "、".join(summary_parts) if summary_parts else None

    sections: list[DraftSection] = []
    if profile.work_experiences:
        sections.append(_work_section(list(profile.work_experiences)))
    if profile.projects:
        sections.append(_project_section(list(profile.projects)))
    if profile.education:
        sections.append(_education_section(list(profile.education)))
    if profile.skills:
        sections.append(_skills_section(list(profile.skills)))
    if profile.certificates:
        sections.append(_certificates_section(list(profile.certificates)))

    return ResumeDraft(
        title=str(identity.get("name") or "我的简历"),
        identity=identity,
        summary=summary,
        sections=sections,
        template_id=TemplateId.CLASSIC,
        design_tokens=DesignTokens(),
    )


# ─────────────────────────── 草稿模型 ↔ schema ───────────────────────────


def _draft_content(draft: ResumeDraft) -> dict[str, Any]:
    """把 ResumeDraft 的可编辑内容序列化为 content JSONB。"""
    return {
        "identity": draft.identity,
        "summary": draft.summary,
        "sections": [s.model_dump(mode="json") for s in draft.sections],
    }


def draft_model_to_schema(model: ResumeDraftModel) -> ResumeDraft:
    """从 ORM 模型重建 ResumeDraft schema。"""
    content = dict(model.content or {})
    tokens = DesignTokens(**model.design_tokens) if model.design_tokens else DesignTokens()
    sections = [DraftSection(**s) for s in content.get("sections", [])]
    return ResumeDraft(
        title=model.title,
        identity=content.get("identity") or {},
        summary=content.get("summary"),
        sections=sections,
        template_id=TemplateId(model.template_id),
        design_tokens=tokens,
    )


# ─────────────────────────── 服务函数 ───────────────────────────


async def create_draft_from_profile(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumeDraftModel:
    """从已解析的候选人画像创建草稿并落库，返回草稿模型。"""
    result = await session.execute(
        select(CandidateProfileModel).where(CandidateProfileModel.resume_id == resume_id),
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError(f"Candidate profile not found for resume: {resume_id}")

    draft = profile_to_draft(profile)
    model = ResumeDraftModel(
        resume_id=resume_id,
        title=draft.title,
        content=_draft_content(draft),
        template_id=draft.template_id.value,
        design_tokens=draft.design_tokens.model_dump(mode="json"),
        auto_one_page=False,
        status="draft",
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model


async def get_draft(session: AsyncSession, draft_id: uuid.UUID) -> ResumeDraftModel:
    """按 id 获取草稿，不存在抛 ValueError。"""
    model = await session.get(ResumeDraftModel, draft_id)
    if model is None:
        raise ValueError(f"Resume draft not found: {draft_id}")
    return model


async def update_draft(
    session: AsyncSession,
    draft_id: uuid.UUID,
    patch: dict[str, Any],
) -> ResumeDraftModel:
    """幂等更新草稿的 content / 模板 / 设计令牌 / 标题 / 自动一页。"""
    model = await get_draft(session, draft_id)

    if "title" in patch and patch["title"]:
        model.title = str(patch["title"])
    if "template_id" in patch and patch["template_id"]:
        model.template_id = TemplateId(patch["template_id"]).value
    if "design_tokens" in patch and patch["design_tokens"] is not None:
        model.design_tokens = DesignTokens(**patch["design_tokens"]).model_dump(mode="json")
    if "auto_one_page" in patch and patch["auto_one_page"] is not None:
        model.auto_one_page = bool(patch["auto_one_page"])

    # content 相关字段（identity / summary / sections）合并进 content JSONB
    content = dict(model.content or {})
    if "identity" in patch and patch["identity"] is not None:
        # photo 为服务端受控字段，仅经 confirm/delete 照片端点写入，
        # 避免绕过归属校验直写任意对象名
        incoming = dict(patch["identity"])
        incoming.pop("photo", None)
        existing_photo = (content.get("identity") or {}).get("photo")
        if existing_photo:
            incoming["photo"] = existing_photo
        content["identity"] = incoming
    if "summary" in patch:
        content["summary"] = patch["summary"]
    if "sections" in patch and patch["sections"] is not None:
        # 用 schema 校验后再序列化，保证结构合法
        validated = [DraftSection(**s) for s in patch["sections"]]
        content["sections"] = [s.model_dump(mode="json") for s in validated]
    model.content = content

    await session.commit()
    await session.refresh(model)
    return model


async def set_draft_photo(
    session: AsyncSession,
    draft_id: uuid.UUID,
    object_name: str | None,
) -> ResumeDraftModel:
    """设置或清除草稿的证件照引用（identity.photo 存 MinIO 对象名）。

    object_name 为 None 时移除 photo 字段；仅改 photo，不触碰 identity 其他字段。
    """
    model = await get_draft(session, draft_id)
    content = dict(model.content or {})
    identity = dict(content.get("identity") or {})
    if object_name is None:
        identity.pop("photo", None)
    else:
        identity["photo"] = object_name
    content["identity"] = identity
    model.content = content

    await session.commit()
    await session.refresh(model)
    return model


async def polish_draft_section(
    gateway: LLMGateway,
    section_type: ResumeSectionType,
    items: list[str],
    context: str | None = None,
) -> PolishResult:
    """对某区块的一组要点做 AI 润色，返回原文 + 建议（保留原文供逐条接受）。"""
    polisher = LLMResumePolisher(gateway)
    return await polisher.polish(section_type, items, context)


def draft_to_parsed_result(draft: ResumeDraft) -> dict[str, Any]:
    """把草稿组装成 evaluator 可用的 parsed_result-like dict。"""
    return {
        "identity": draft.identity,
        "summary": draft.summary,
        "sections": [s.model_dump(mode="json") for s in draft.sections],
    }


async def score_draft(gateway: LLMGateway, draft: ResumeDraft) -> dict[str, Any]:
    """复用 9 维评估器对草稿打分。"""
    evaluator = LLMResumeEvaluator(gateway)
    parsed_result = draft_to_parsed_result(draft)
    return await evaluator.evaluate(parsed_result)


def draft_photo_data_uri(draft: ResumeDraft) -> str | None:
    """把草稿照片（identity.photo 存 MinIO 对象名）读为 base64 data URI。

    无照片返回 None；读取失败降级为 None（不阻断预览/导出）。
    同步网络 I/O，调用方需用 asyncio.to_thread 包裹。
    """
    object_name = draft.identity.get("photo") if draft.identity else None
    if not object_name:
        return None
    settings = get_settings()
    try:
        photo_bytes = download_file(settings.MINIO_BUCKET_PHOTOS, str(object_name))
    except Exception:
        logger.warning("读取草稿照片失败，降级为无照片渲染: %s", object_name, exc_info=True)
        return None
    encoded = base64.b64encode(photo_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_draft_html(draft: ResumeDraft, photo_data_uri: str | None = None) -> str:
    """渲染草稿为预览 HTML。"""
    return HtmlRenderer().render(draft, photo_data_uri=photo_data_uri)


async def export_draft_pdf(
    session: AsyncSession,
    draft_model: ResumeDraftModel,
    options: ExportOptions,
) -> tuple[bytes, ExportResult]:
    """渲染 HTML → Playwright 出 PDF →（可选）上传 MinIO 并记录导出历史。"""
    draft = draft_model_to_schema(draft_model)
    if options.template_id is not None:
        draft.template_id = options.template_id

    # 照片以 data URI 内联，Playwright 离线打印无外部网络请求
    photo_data_uri = await asyncio.to_thread(draft_photo_data_uri, draft)

    pdf_bytes, page_count, overflow = await PdfRenderer().render_pdf(
        draft, auto_one_page=options.auto_one_page, photo_data_uri=photo_data_uri,
    )

    storage_path: str | None = None
    if options.persist:
        settings = get_settings()
        ensure_bucket(settings.MINIO_BUCKET_EXPORTS)
        storage_path = f"{draft_model.id}/{uuid.uuid4()}.pdf"
        upload_file(
            bucket=settings.MINIO_BUCKET_EXPORTS,
            object_name=storage_path,
            data=pdf_bytes,
            content_type="application/pdf",
        )
        session.add(ResumeExportModel(
            draft_id=draft_model.id,
            storage_path=storage_path,
            template_id=draft.template_id.value,
            page_count=page_count,
        ))
        await session.commit()

    return pdf_bytes, ExportResult(
        page_count=page_count, overflow=overflow, storage_path=storage_path,
    )
