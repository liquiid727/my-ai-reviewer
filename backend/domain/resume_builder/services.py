"""简历制作领域服务 —— 草稿创建/更新、AI 润色、AI 打分、PDF 导出。"""

from __future__ import annotations

import base64
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.privacy import PrivacyGuard, ResumePrivacyRedactor, apply_privacy_replacements
from backend.domain.privacy.redactor import TOKEN_RE
from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.editing import DraftRevisionConflictError
from backend.domain.resume_builder.enums import LayoutMode, TemplateId
from backend.domain.resume_builder.schemas import (
    DesignTokens,
    DraftItem,
    DraftSection,
    ExportOptions,
    ExportResult,
    LayoutPolicy,
    PolishResult,
    ResumeDraft,
)
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    ResumeDraftModel,
)
from backend.infrastructure.evaluators.llm_evaluator import LLMResumeEvaluator
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.polishers.llm_polisher import LLMResumePolisher
from backend.infrastructure.rendering.html_renderer import HtmlRenderer
from backend.infrastructure.rendering.pdf_renderer import PdfRenderer
from backend.infrastructure.storage.minio_client import download_file

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
        items.append(
            DraftItem(
                heading=w.get("company"),
                subheading=w.get("title"),
                date_range=_join_date(w.get("start_date"), w.get("end_date")),
                bullets=bullets,
            )
        )
    return DraftSection(
        section_type=ResumeSectionType.WORK_EXPERIENCE,
        title="工作经历",
        items=items,
        order=1,
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
        items.append(
            DraftItem(
                heading=p.get("name"),
                subheading=p.get("role"),
                bullets=bullets,
            )
        )
    return DraftSection(
        section_type=ResumeSectionType.PROJECT_EXPERIENCE,
        title="项目经历",
        items=items,
        order=2,
    )


def _education_section(education: list[dict[str, Any]]) -> DraftSection:
    items: list[DraftItem] = []
    for e in education:
        degree_major = " ".join(x for x in [e.get("degree"), e.get("major")] if x)
        bullets = [f"GPA: {e['gpa']}"] if e.get("gpa") else []
        items.append(
            DraftItem(
                heading=e.get("school"),
                subheading=degree_major or None,
                date_range=_join_date(e.get("start_date"), e.get("end_date")),
                bullets=bullets,
            )
        )
    return DraftSection(
        section_type=ResumeSectionType.EDUCATION,
        title="教育背景",
        items=items,
        order=3,
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
        title="技能",
        items=[DraftItem(bullets=bullets)] if bullets else [],
        order=4,
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
        title="证书",
        items=[DraftItem(bullets=bullets)] if bullets else [],
        order=5,
    )


def profile_to_draft(profile: CandidateProfileModel) -> ResumeDraft:
    """Map a candidate profile to an editable draft (bulletized, classic + normal).

    Returns an *unsanitized* draft. Callers that persist must run a single
    `_sanitize_draft_for_persistence` pass and keep the produced manifest —
    double-sanitizing already-masked content yields empty placeholders and
    breaks export hydration.
    """
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


def _sanitize_draft_for_persistence(draft: ResumeDraft) -> tuple[ResumeDraft, dict[str, Any]]:
    """Redact every user-editable string before persisting a draft.

    Only newly-redacted cleartext contributes placeholders. Already-masked
    ``[[TYPE_NN]]`` tokens are left untouched and produce no entries — callers
    that update an existing draft must merge with the prior manifest (see
    `_merge_privacy_manifests`) so export hydration keeps working.
    """
    counters: dict[str, int] = defaultdict(int)
    placeholders: list[dict[str, Any]] = []

    protected_keys = {
        "title",
        "section_type",
        "template_id",
        "density",
        "mode",
        "layout_mode",
        "target_page_count",
        "order",
        "visible",
        "item_id",
        "section_id",
        # MinIO object-name refs are storage handles, not PII values.
        "photo",
    }

    def redact(value: Any, key: str | None = None) -> Any:
        if key in protected_keys and not (key == "title" and value not in {"我的简历", "Resume", "简历"}):
            return value
        if isinstance(value, str):
            result = ResumePrivacyRedactor().redact(value)
            text = result.masked_text
            for placeholder in result.manifest.placeholders:
                counters[placeholder.entity_type] += 1
                prefix = "ORG" if placeholder.entity_type == "organization" else placeholder.entity_type.upper()
                token = f"[[{prefix}_{counters[placeholder.entity_type]:02d}]]"
                text = text.replace(placeholder.token, token)
                placeholders.append(placeholder.model_copy(update={"token": token}).model_dump(mode="json"))
            return text
        if isinstance(value, list):
            return [redact(item, key) for item in value]
        if isinstance(value, dict):
            return {child_key: redact(item, child_key) for child_key, item in value.items()}
        return value

    sanitized = redact(draft.model_dump(mode="json"))
    clean = ResumeDraft(**sanitized)
    PrivacyGuard().assert_masked(clean.model_dump(mode="json"))
    return clean, {"placeholders": placeholders, "policy_version": "resume-privacy-v1"}


def _collect_tokens_from_value(value: Any, out: set[str]) -> None:
    """Recursively collect ``[[TYPE_NN]]`` tokens present in structured content."""
    if isinstance(value, str):
        out.update(TOKEN_RE.findall(value))
        return
    if isinstance(value, list):
        for item in value:
            _collect_tokens_from_value(item, out)
        return
    if isinstance(value, dict):
        for item in value.values():
            _collect_tokens_from_value(item, out)


def _entity_type_from_token(token: str) -> str:
    """Best-effort entity_type recovery from a placeholder token string."""
    inner = token.strip("[]")
    prefix = inner.rsplit("_", 1)[0].lower() if "_" in inner else inner.lower()
    if prefix == "org":
        return "organization"
    return prefix


def _merge_privacy_manifests(
    existing: dict[str, Any] | None,
    newly_redacted: dict[str, Any],
    content: dict[str, Any] | ResumeDraft | None = None,
) -> dict[str, Any]:
    """Merge newly redacted placeholders into an existing draft manifest.

    Rules:
    - Never blank a non-empty prior manifest with ``placeholders: []`` just
      because a re-sanitize of already-masked content found nothing new.
    - Prefer the newest entry when the same token is redacted again.
    - Also retain any ``[[TYPE_NN]]`` tokens still present in content even if
      they were dropped from both manifests (content is source of truth for
      "still in use").
    """
    by_token: dict[str, dict[str, Any]] = {}

    def _ingest(manifest: dict[str, Any] | None) -> None:
        if not isinstance(manifest, dict):
            return
        raw = manifest.get("placeholders") or []
        if not isinstance(raw, list):
            return
        for item in raw:
            if not isinstance(item, dict):
                continue
            token = item.get("token")
            if isinstance(token, str) and token:
                by_token[token] = dict(item)

    _ingest(existing)
    _ingest(newly_redacted)

    # Content-scan: keep tokens still present even if a stale entry was dropped.
    present: set[str] = set()
    if content is not None:
        payload = content.model_dump(mode="json") if isinstance(content, ResumeDraft) else content
        _collect_tokens_from_value(payload, present)
        for token in present:
            if token not in by_token:
                by_token[token] = {
                    "token": token,
                    "entity_type": _entity_type_from_token(token),
                }

    # Drop entries whose tokens no longer appear in content when we scanned it.
    if present:
        by_token = {token: entry for token, entry in by_token.items() if token in present}

    policy = "resume-privacy-v1"
    for source in (newly_redacted, existing or {}):
        if isinstance(source, dict) and source.get("policy_version"):
            policy = str(source["policy_version"])
            break

    return {
        "placeholders": list(by_token.values()),
        "policy_version": policy,
    }


def _allowed_tokens_for_export(
    privacy_manifest: dict[str, Any] | None,
    draft: ResumeDraft,
) -> set[str]:
    """Union of manifest-declared tokens and tokens still present in content."""
    allowed: set[str] = set()
    placeholders = (privacy_manifest or {}).get("placeholders", [])
    if isinstance(placeholders, list):
        for item in placeholders:
            if not isinstance(item, dict):
                continue
            token = item.get("token")
            if isinstance(token, str) and token:
                allowed.add(token)
    _collect_tokens_from_value(draft.model_dump(mode="json"), allowed)
    return allowed


def _validate_photo_object_name(object_name: str) -> str:
    """Reject embedded data-URIs / base64 blobs; accept MinIO object-name refs."""
    value = object_name.strip()
    if not value:
        raise ValueError("Photo object name must not be empty")
    lowered = value.lower()
    if lowered.startswith("data:"):
        raise ValueError("Photo must be a storage object name, not a data URI")
    if "base64," in lowered:
        raise ValueError("Photo must be a storage object name, not embedded base64")
    # Heuristic: real object names are short paths; data payloads are huge.
    if len(value) > 512:
        raise ValueError("Photo object name is implausibly long")
    if any(ch.isspace() for ch in value):
        raise ValueError("Photo object name must not contain whitespace")
    return value


def draft_model_to_schema(model: ResumeDraftModel) -> ResumeDraft:
    """从 ORM 模型重建 ResumeDraft schema。"""
    content = dict(model.content or {})
    tokens = DesignTokens(**model.design_tokens) if model.design_tokens else DesignTokens()
    sections: list[DraftSection] = []
    for section_index, raw_section in enumerate(content.get("sections", [])):
        section_data = dict(raw_section)
        section_data.setdefault(
            "section_id",
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"resume-draft:{model.id}:section:{section_index}")),
        )
        items: list[dict[str, Any]] = []
        for item_index, raw_item in enumerate(section_data.get("items", [])):
            item_data = dict(raw_item)
            item_data.setdefault(
                "item_id",
                str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"resume-draft:{model.id}:section:{section_index}:item:{item_index}",
                    ),
                ),
            )
            items.append(item_data)
        section_data["items"] = items
        sections.append(DraftSection(**section_data))
    return ResumeDraft(
        title=model.title,
        identity=content.get("identity") or {},
        summary=content.get("summary"),
        sections=sections,
        template_id=TemplateId(model.template_id),
        design_tokens=tokens,
        layout_policy=LayoutPolicy(
            mode=LayoutMode(model.layout_mode),
            target_page_count=model.target_page_count,
        ),
    )


def hydrate_draft_for_export(
    draft: ResumeDraft,
    replacements: dict[str, str],
    *,
    allowed_tokens: set[str],
) -> ResumeDraft:
    """Hydrate a short-lived structured copy for preview/export only."""
    hydrated = apply_privacy_replacements(
        draft.model_dump(mode="json"),
        replacements,
        allowed_tokens=allowed_tokens,
    )
    return ResumeDraft(**hydrated)


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

    # Single sanitize pass: profile_to_draft is unsanitized; the manifest from
    # this pass is the one that actually redacted PII and must be persisted.
    draft, privacy_manifest = _sanitize_draft_for_persistence(profile_to_draft(profile))
    # 新建草稿放在列表首位，保持用户刚创建的草稿可立即找到。
    await session.execute(
        update(ResumeDraftModel).values(
            sort_order=ResumeDraftModel.sort_order + 1,
            updated_at=ResumeDraftModel.updated_at,
        ),
    )
    model = ResumeDraftModel(
        resume_id=resume_id,
        title=draft.title,
        content=_draft_content(draft),
        template_id=draft.template_id.value,
        design_tokens=draft.design_tokens.model_dump(mode="json"),
        layout_mode=draft.layout_policy.mode.value,
        target_page_count=draft.layout_policy.target_page_count,
        status="draft",
        sort_order=0,
        privacy_manifest=privacy_manifest,
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model


async def create_draft_from_reference(
    session: AsyncSession,
    template_key: str,
) -> ResumeDraftModel:
    """从内置参考模板创建独立草稿（resume_id 为空），不存在抛 ValueError。"""
    # 延迟导入避免循环依赖（reference_templates 依赖本包 schemas）
    from backend.domain.resume_builder.reference_templates import get_reference_template

    template = get_reference_template(template_key)
    if template is None:
        raise ValueError(f"Reference template not found: {template_key}")

    draft, privacy_manifest = _sanitize_draft_for_persistence(template.build_draft())
    # 新建草稿放在列表首位，保持用户刚创建的草稿可立即找到。
    await session.execute(
        update(ResumeDraftModel).values(
            sort_order=ResumeDraftModel.sort_order + 1,
            updated_at=ResumeDraftModel.updated_at,
        ),
    )
    model = ResumeDraftModel(
        resume_id=None,
        title=draft.title,
        content=_draft_content(draft),
        template_id=draft.template_id.value,
        design_tokens=draft.design_tokens.model_dump(mode="json"),
        layout_mode=draft.layout_policy.mode.value,
        target_page_count=draft.layout_policy.target_page_count,
        status="draft",
        sort_order=0,
        privacy_manifest=privacy_manifest,
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model


async def list_drafts(session: AsyncSession) -> list[ResumeDraftModel]:
    """返回全部草稿，按用户维护的列表顺序返回。"""
    result = await session.execute(
        select(ResumeDraftModel).order_by(
            ResumeDraftModel.sort_order.asc(),
            ResumeDraftModel.updated_at.desc(),
            ResumeDraftModel.created_at.desc(),
        ),
    )
    return list(result.scalars().all())


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
    expected_revision: int | None = None,
) -> ResumeDraftModel:
    """幂等更新草稿内容、模板、设计令牌、标题和分页策略。"""
    model: ResumeDraftModel
    if expected_revision is None:
        model = await get_draft(session, draft_id)
    else:
        result = await session.execute(
            select(ResumeDraftModel).where(ResumeDraftModel.id == draft_id).with_for_update(),
        )
        locked_model = result.scalar_one_or_none()
        if locked_model is None:
            raise ValueError(f"Resume draft not found: {draft_id}")
        model = locked_model
        if model.revision != expected_revision:
            raise DraftRevisionConflictError(expected_revision, model.revision)

    if "title" in patch and patch["title"]:
        model.title = str(patch["title"])
    if "template_id" in patch and patch["template_id"]:
        model.template_id = TemplateId(patch["template_id"]).value
    if "design_tokens" in patch and patch["design_tokens"] is not None:
        model.design_tokens = DesignTokens(**patch["design_tokens"]).model_dump(mode="json")
    if "layout_policy" in patch and patch["layout_policy"] is not None:
        policy = LayoutPolicy(**patch["layout_policy"])
        model.layout_mode = policy.mode.value
        model.target_page_count = policy.target_page_count

    # content 相关字段（identity / summary / sections）合并进 content JSONB
    content = dict(model.content or {})
    if "identity" in patch and patch["identity"] is not None:
        # Client-supplied photo must never bypass confirm ownership checks.
        # Existing confirmed photo (set via set_draft_photo) is preserved.
        existing = dict(content.get("identity") or {})
        existing_photo = existing.get("photo")
        incoming = dict(patch["identity"])
        incoming.pop("photo", None)
        merged = {**existing, **incoming}
        if existing_photo is not None:
            merged["photo"] = existing_photo
        else:
            merged.pop("photo", None)
        content["identity"] = merged
    if "summary" in patch:
        content["summary"] = patch["summary"]
    if "sections" in patch and patch["sections"] is not None:
        # 用 schema 校验后再序列化，保证结构合法
        validated = [DraftSection(**s) for s in patch["sections"]]
        content["sections"] = [s.model_dump(mode="json") for s in validated]
    candidate = ResumeDraft(
        title=model.title,
        identity=content.get("identity") or {},
        summary=content.get("summary"),
        sections=[DraftSection(**section) for section in content.get("sections", [])],
        template_id=TemplateId(model.template_id),
        design_tokens=DesignTokens(**(model.design_tokens or {})),
        layout_policy=LayoutPolicy(
            mode=LayoutMode(model.layout_mode),
            target_page_count=model.target_page_count,
        ),
    )
    candidate, newly_redacted = _sanitize_draft_for_persistence(candidate)
    # Re-sanitizing already-masked content yields empty placeholders — merge
    # with the prior manifest (and tokens still present in content) so we never
    # wipe a good manifest with placeholders: [].
    existing_manifest = getattr(model, "privacy_manifest", None)
    if not isinstance(existing_manifest, dict):
        existing_manifest = None
    content_payload = _draft_content(candidate)
    privacy_manifest = _merge_privacy_manifests(
        existing_manifest,
        newly_redacted,
        content=content_payload,
    )
    model.title = candidate.title
    model.content = content_payload
    model.design_tokens = candidate.design_tokens.model_dump(mode="json")
    model.layout_mode = candidate.layout_policy.mode.value
    model.target_page_count = candidate.layout_policy.target_page_count
    model.privacy_manifest = privacy_manifest
    model.revision = int(getattr(model, "revision", 0)) + 1

    await session.commit()
    await session.refresh(model)
    return model


async def delete_draft(session: AsyncSession, draft_id: uuid.UUID) -> None:
    """删除草稿及其级联导出记录。"""
    model = await get_draft(session, draft_id)
    await session.delete(model)
    await session.commit()


async def reorder_drafts(
    session: AsyncSession,
    draft_ids: list[uuid.UUID],
) -> list[ResumeDraftModel]:
    """按前端提交的完整 id 顺序持久化草稿列表。"""
    if len(draft_ids) != len(set(draft_ids)):
        raise ValueError("Draft order contains duplicate ids")

    result = await session.execute(select(ResumeDraftModel))
    models = list(result.scalars().all())
    by_id = {model.id: model for model in models}
    if set(by_id) != set(draft_ids):
        raise ValueError("Draft order must include every draft exactly once")

    for index, draft_id in enumerate(draft_ids):
        await session.execute(
            update(ResumeDraftModel)
            .where(ResumeDraftModel.id == draft_id)
            .values(
                sort_order=index,
                updated_at=ResumeDraftModel.updated_at,
            ),
        )

    await session.commit()
    session.expire_all()
    return await list_drafts(session)


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
        identity["photo"] = _validate_photo_object_name(object_name)
    content["identity"] = identity
    model.content = content
    model.revision = int(getattr(model, "revision", 0)) + 1

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
    PrivacyGuard().assert_masked({"items": items, "context": context})
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
    PrivacyGuard().assert_masked(draft.model_dump(mode="json"))
    evaluator = LLMResumeEvaluator(gateway)
    parsed_result = draft_to_parsed_result(draft)
    return await evaluator.evaluate(parsed_result)


async def save_draft_score(
    session: AsyncSession,
    draft_id: uuid.UUID,
    evaluation: dict[str, Any],
) -> ResumeDraftModel:
    """把最新评分结果持久化到草稿，记录评分时间与评分时的 revision。"""
    model = await get_draft(session, draft_id)
    model.latest_score = evaluation
    model.scored_at = datetime.now(timezone.utc)
    model.scored_revision = int(getattr(model, "revision", 1))
    await session.commit()
    await session.refresh(model)
    return model


def serialize_draft_score(model: ResumeDraftModel) -> dict[str, Any] | None:
    """序列化草稿的持久化评分；未评分时返回 None。"""
    if not model.latest_score:
        return None
    payload = dict(model.latest_score)
    payload.pop("_meta", None)
    payload["scored_at"] = model.scored_at.isoformat() if model.scored_at else None
    payload["scored_revision"] = model.scored_revision
    return payload


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
    photo_data_uri: str | None = None,
) -> tuple[bytes, ExportResult]:
    """渲染 HTML → Playwright 出 PDF →（可选）上传 MinIO 并记录导出历史。"""
    draft = draft_model_to_schema(draft_model)
    if options.template_id is not None:
        draft.template_id = options.template_id

    # Manifest tokens ∪ tokens still present in content — never reject a
    # replacement solely because a prior double-sanitize wiped the manifest.
    allowed_tokens = _allowed_tokens_for_export(
        getattr(draft_model, "privacy_manifest", None),
        draft,
    )
    draft = hydrate_draft_for_export(draft, options.replacements, allowed_tokens=allowed_tokens)

    layout_policy = options.layout_policy or draft.layout_policy
    pdf_bytes, page_count, target_met, applied_density = await PdfRenderer().render_pdf(
        draft,
        layout_policy=layout_policy,
        photo_data_uri=photo_data_uri,
    )

    return pdf_bytes, ExportResult(
        page_count=page_count,
        target_met=target_met,
        applied_density=applied_density,
        storage_path=None,
    )
