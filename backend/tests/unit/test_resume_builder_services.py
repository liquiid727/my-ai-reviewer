"""简历制作领域服务的单元测试（免数据库的纯逻辑部分）。"""

from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.enums import LayoutMode, TemplateId
from backend.domain.resume_builder.schemas import DesignTokens, LayoutPolicy, ResumeDraft
from backend.domain.resume_builder.services import (
    _allowed_tokens_for_export,
    _draft_content,
    _merge_privacy_manifests,
    _sanitize_draft_for_persistence,
    _validate_photo_object_name,
    draft_model_to_schema,
    draft_to_parsed_result,
    hydrate_draft_for_export,
    profile_to_draft,
    set_draft_photo,
    update_draft,
)


class _FakeProfile:
    """模拟 CandidateProfileModel 的最小对象（免数据库）。"""

    def __init__(self, **kwargs: object) -> None:
        self.identity = kwargs.get("identity", {})
        self.education = kwargs.get("education", [])
        self.work_experiences = kwargs.get("work_experiences", [])
        self.projects = kwargs.get("projects", [])
        self.skills = kwargs.get("skills", [])
        self.certificates = kwargs.get("certificates", [])
        self.ability_tags = kwargs.get("ability_tags", [])
        self.interview_clues = kwargs.get("interview_clues", [])
        self.risks = kwargs.get("risks", [])


class _FakeDraftModel:
    """模拟 ResumeDraftModel 的最小对象（免数据库）。"""

    def __init__(
        self,
        content: dict[str, Any],
        template_id: str = "classic",
        design_tokens: dict[str, Any] | None = None,
        layout_mode: str = "auto_pages",
        target_page_count: int | None = None,
        title: str = "我的简历",
        privacy_manifest: dict[str, Any] | None = None,
    ) -> None:
        import uuid

        self.id = uuid.uuid4()
        self.content: dict[str, Any] = content
        self.template_id = template_id
        self.design_tokens = design_tokens or {}
        self.layout_mode = layout_mode
        self.target_page_count = target_page_count
        self.title = title
        self.privacy_manifest: dict[str, Any] = privacy_manifest or {}
        self.revision = 0


class _FakeSession:
    async def commit(self) -> None:
        pass

    async def refresh(self, model: Any) -> None:
        pass


def _session() -> AsyncSession:
    return cast(AsyncSession, _FakeSession())


def test_profile_to_draft_maps_sections() -> None:
    """profile_to_draft is unsanitized; single sanitize pass masks PII + builds manifest.

    RIP-009: draft materialization persists masked identity only (no cleartext PII).
    The create path runs sanitize exactly once and retains the real manifest.
    """
    profile = _FakeProfile(
        identity={"name": "张三", "email": "z@example.com"},
        work_experiences=[
            {
                "company": "字节跳动",
                "title": "后端工程师",
                "start_date": "2020",
                "end_date": "2023",
                "responsibilities": ["负责订单系统"],
                "achievements": ["QPS 提升 3 倍"],
            }
        ],
        projects=[{"name": "支付网关", "role": "负责人", "highlights": ["高可用"]}],
        education=[{"school": "清华", "degree": "硕士", "major": "计算机", "gpa": "3.9"}],
        skills=[{"name": "Python", "category": "programming_language"}],
        certificates=[{"name": "PMP", "issuer": "PMI"}],
        ability_tags=["高并发", "分布式"],
    )
    raw = profile_to_draft(profile)  # type: ignore[arg-type]
    # Mapping itself is cleartext — sanitize is the single persistence gate.
    assert raw.identity["name"] == "张三"
    assert raw.identity["email"] == "z@example.com"

    draft, manifest = _sanitize_draft_for_persistence(raw)

    # RIP-009: after the single sanitize pass, identity is masked not cleartext.
    assert draft.title == "[[PERSON_01]]"
    assert str(draft.identity["name"]).startswith("[[PERSON_")
    assert draft.identity["email"] == "[[EMAIL_01]]"
    assert draft.summary == "高并发、分布式"
    assert draft.template_id == TemplateId.CLASSIC

    # Manifest from the pass that actually redacted PII must retain tokens.
    tokens = {p["token"] for p in manifest["placeholders"]}
    assert any(t.startswith("[[PERSON_") for t in tokens)
    assert "[[EMAIL_01]]" in tokens
    # Export allowed_tokens built from that manifest accept the replacements.
    allowed = _allowed_tokens_for_export(manifest, draft)
    assert "[[EMAIL_01]]" in allowed
    assert any(t.startswith("[[PERSON_") for t in allowed)
    hydrated = hydrate_draft_for_export(
        draft,
        {draft.identity["name"]: "张三", "[[EMAIL_01]]": "z@example.com"},
        allowed_tokens=allowed,
    )
    assert hydrated.identity["name"] == "张三"
    assert hydrated.identity["email"] == "z@example.com"

    types = {s.section_type for s in draft.sections}
    assert ResumeSectionType.WORK_EXPERIENCE in types
    assert ResumeSectionType.PROJECT_EXPERIENCE in types
    assert ResumeSectionType.EDUCATION in types
    assert ResumeSectionType.SKILLS in types
    assert ResumeSectionType.CERTIFICATES in types

    work = next(s for s in draft.sections if s.section_type == ResumeSectionType.WORK_EXPERIENCE)
    assert work.items[0].heading is not None
    assert work.items[0].heading.startswith("[[")
    assert work.items[0].date_range == "2020 ~ 2023"
    # responsibilities + achievements 合并为 bullets
    assert "负责订单系统" in work.items[0].bullets
    assert "QPS 提升 3 倍" in work.items[0].bullets


def test_profile_to_draft_empty_profile() -> None:
    draft = profile_to_draft(_FakeProfile())  # type: ignore[arg-type]
    assert draft.title == "我的简历"
    assert draft.sections == []
    assert draft.summary is None


def test_double_sanitize_would_empty_manifest_but_create_path_does_not() -> None:
    """Regression lock: second sanitize of already-masked draft yields no new placeholders.

    create_draft_from_profile must sanitize once; double-sanitize is the P1 bug.
    """
    raw = profile_to_draft(
        _FakeProfile(identity={"name": "张三", "email": "z@example.com"}),  # type: ignore[arg-type]
    )
    once, manifest_once = _sanitize_draft_for_persistence(raw)
    assert manifest_once["placeholders"], "first pass must produce real placeholders"
    _twice, manifest_twice = _sanitize_draft_for_persistence(once)
    assert manifest_twice["placeholders"] == [], (
        "second sanitize of masked content finds nothing — must not be persisted alone"
    )
    # Merge recovers the real manifest (what update_draft / create must do).
    merged = _merge_privacy_manifests(manifest_once, manifest_twice, content=once)
    tokens = {p["token"] for p in merged["placeholders"]}
    assert "[[EMAIL_01]]" in tokens
    assert any(t.startswith("[[PERSON_") for t in tokens)


@pytest.mark.asyncio
async def test_update_draft_does_not_wipe_existing_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """update_draft on already-masked content must keep prior placeholders."""
    existing_manifest = {
        "placeholders": [
            {"token": "[[PERSON_01]]", "entity_type": "person"},
            {"token": "[[EMAIL_01]]", "entity_type": "email"},
        ],
        "policy_version": "resume-privacy-v1",
    }
    model = _FakeDraftModel(
        content={
            "identity": {"name": "[[PERSON_01]]", "email": "[[EMAIL_01]]"},
            "summary": None,
            "sections": [],
        },
        title="[[PERSON_01]]",
        privacy_manifest=existing_manifest,
    )

    async def fake_get_draft(session: Any, draft_id: Any) -> Any:
        return model

    monkeypatch.setattr("backend.domain.resume_builder.services.get_draft", fake_get_draft)

    await update_draft(
        _session(),
        model.id,
        {"summary": "资深工程师"},  # no new PII — sanitize finds nothing
    )

    placeholders = model.privacy_manifest.get("placeholders") or []
    tokens = {p["token"] for p in placeholders if isinstance(p, dict)}
    assert "[[PERSON_01]]" in tokens
    assert "[[EMAIL_01]]" in tokens
    # Content stays masked; new summary passes through (no PII).
    assert model.content["identity"]["name"] == "[[PERSON_01]]"
    assert model.content["summary"] == "资深工程师"


@pytest.mark.asyncio
async def test_update_draft_merges_new_redactions_into_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """New cleartext PII on update is redacted and merged into the prior manifest."""
    existing_manifest = {
        "placeholders": [{"token": "[[PERSON_01]]", "entity_type": "person"}],
        "policy_version": "resume-privacy-v1",
    }
    model = _FakeDraftModel(
        content={
            "identity": {"name": "[[PERSON_01]]"},
            "summary": None,
            "sections": [],
        },
        title="[[PERSON_01]]",
        privacy_manifest=existing_manifest,
    )

    async def fake_get_draft(session: Any, draft_id: Any) -> Any:
        return model

    monkeypatch.setattr("backend.domain.resume_builder.services.get_draft", fake_get_draft)

    await update_draft(
        _session(),
        model.id,
        {"identity": {"name": "[[PERSON_01]]", "email": "new@example.com"}},
    )

    tokens = {p["token"] for p in model.privacy_manifest["placeholders"]}
    assert "[[PERSON_01]]" in tokens
    assert any("EMAIL" in t for t in tokens)
    assert str(model.content["identity"]["email"]).startswith("[[EMAIL_")


def test_allowed_tokens_union_manifest_and_content() -> None:
    """Export allowed_tokens includes content-present tokens even if manifest is empty."""
    draft = ResumeDraft(
        title="[[PERSON_01]]",
        identity={"name": "[[PERSON_01]]", "email": "[[EMAIL_01]]"},
    )
    # Empty manifest (the double-sanitize failure mode) must still allow content tokens.
    allowed = _allowed_tokens_for_export({"placeholders": []}, draft)
    assert "[[PERSON_01]]" in allowed
    assert "[[EMAIL_01]]" in allowed
    hydrated = hydrate_draft_for_export(
        draft,
        {"[[PERSON_01]]": "张三", "[[EMAIL_01]]": "z@example.com"},
        allowed_tokens=allowed,
    )
    assert hydrated.identity["name"] == "张三"
    assert hydrated.identity["email"] == "z@example.com"


def test_validate_photo_object_name_accepts_minio_refs() -> None:
    assert _validate_photo_object_name("d1/processed-legit.png") == "d1/processed-legit.png"
    assert _validate_photo_object_name("draft-uuid/processed-x.png") == "draft-uuid/processed-x.png"


def test_validate_photo_object_name_rejects_data_uri_and_base64() -> None:
    with pytest.raises(ValueError, match="data URI"):
        _validate_photo_object_name("data:image/png;base64,iVBORw0KGgo=")
    with pytest.raises(ValueError, match="base64"):
        _validate_photo_object_name("inline;base64,AAAA")
    with pytest.raises(ValueError, match="empty"):
        _validate_photo_object_name("   ")
    with pytest.raises(ValueError, match="long"):
        _validate_photo_object_name("x" * 600)


@pytest.mark.asyncio
async def test_set_draft_photo_rejects_data_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeDraftModel(content={"identity": {}, "summary": None, "sections": []})

    async def fake_get_draft(session: Any, draft_id: Any) -> Any:
        return model

    monkeypatch.setattr("backend.domain.resume_builder.services.get_draft", fake_get_draft)

    with pytest.raises(ValueError, match="data URI"):
        await set_draft_photo(_session(), model.id, "data:image/png;base64,abc")


@pytest.mark.asyncio
async def test_set_draft_photo_accepts_object_name(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeDraftModel(content={"identity": {}, "summary": None, "sections": []})

    async def fake_get_draft(session: Any, draft_id: Any) -> Any:
        return model

    monkeypatch.setattr("backend.domain.resume_builder.services.get_draft", fake_get_draft)

    await set_draft_photo(_session(), model.id, "d1/processed-legit.png")
    assert model.content["identity"]["photo"] == "d1/processed-legit.png"


def test_draft_content_roundtrip() -> None:
    original = ResumeDraft(
        title="我的简历",
        identity={"name": "李四"},
        summary="资深工程师",
        sections=[],
        template_id=TemplateId.MODERN,
        design_tokens=DesignTokens(accent_color="#ff0000"),
        layout_policy=LayoutPolicy(mode=LayoutMode.TARGET_PAGES, target_page_count=2),
    )
    model = _FakeDraftModel(
        content=_draft_content(original),
        template_id="modern",
        design_tokens=original.design_tokens.model_dump(mode="json"),
        layout_mode="target_pages",
        target_page_count=2,
        title="我的简历",
    )
    restored = draft_model_to_schema(model)  # type: ignore[arg-type]

    assert restored.identity == {"name": "李四"}
    assert restored.summary == "资深工程师"
    assert restored.template_id == TemplateId.MODERN
    assert restored.design_tokens.accent_color == "#ff0000"
    assert restored.layout_policy == LayoutPolicy(
        mode=LayoutMode.TARGET_PAGES,
        target_page_count=2,
    )


def test_draft_to_parsed_result_shape() -> None:
    draft = ResumeDraft(title="t", identity={"name": "王五"}, summary="s", sections=[])
    parsed = draft_to_parsed_result(draft)
    assert parsed["identity"] == {"name": "王五"}
    assert parsed["summary"] == "s"
    assert parsed["sections"] == []
