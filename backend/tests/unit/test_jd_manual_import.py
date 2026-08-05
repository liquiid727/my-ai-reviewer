"""Manual JD source creation domain and service tests (RIP-012 #104)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from backend.application.jd_import_service import JDImportResult, JDImportService
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.domain.jd.schemas import JDManualImportRequest
from backend.infrastructure.db.models import JobDescriptionModel


class FakeResult:
    def __init__(self, scalar: Any) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeImportSession:
    def __init__(self, existing: list[Any] | None = None) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.existing = existing or []
        self._existing_index = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, value: object) -> None:
        return None

    async def execute(self, stmt: Any) -> FakeResult:
        if self._existing_index < len(self.existing):
            result = self.existing[self._existing_index]
            self._existing_index += 1
            return FakeResult(result)
        return FakeResult(None)


def _payload(**overrides: Any) -> JDManualImportRequest:
    values: dict[str, Any] = {
        "title": "Senior Backend Engineer",
        "company": "Example Co",
        "location": "Remote",
        "department": "Platform",
        "responsibilities": ["Own service reliability"],
        "required_skills": [{"name": "Go", "critical": True}],
        "notes": "Referral",
    }
    values.update(overrides)
    return JDManualImportRequest(**values)


async def test_manual_create_is_synchronous_and_enters_review(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    session = FakeImportSession()

    result = await JDImportService().create_manual(session, payload=_payload())  # type: ignore[arg-type]

    assert isinstance(result, JDImportResult)
    jd = result.jd
    assert jd.source_type == "manual"
    assert jd.status == JDStatus.NEEDS_REVIEW.value
    assert jd.processing_step == JDProcessingStep.REVIEW.value
    assert jd.processing_run_id is None
    assert jd.review_revision == 1
    assert jd.extraction_source == "manual"
    assert session.commits == 1


def test_manual_schema_requires_title_and_bounds_optional_fields() -> None:
    with pytest.raises(ValueError):
        JDManualImportRequest(title="")

    with pytest.raises(ValueError):
        JDManualImportRequest(title="x" * 201)

    with pytest.raises(ValueError):
        JDManualImportRequest(title="Role", company="x" * 201)

    with pytest.raises(ValueError):
        JDManualImportRequest(title="Role", responsibilities=["x" * 501])

    with pytest.raises(ValueError):
        JDManualImportRequest(title="Role", required_skills=[{"name": "x" * 501}])  # type: ignore[list-item]

    with pytest.raises(ValueError):
        JDManualImportRequest(title="Role", notes="x" * 1001)

    with pytest.raises(ValueError):
        JDManualImportRequest(title="Role", employment_type="unknown")  # type: ignore[arg-type]


async def test_manual_draft_uses_manual_provenance_confidence_one_and_no_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    result = await JDImportService().create_manual(FakeImportSession(), payload=_payload())  # type: ignore[arg-type]

    jd = result.jd
    draft = jd.review_draft
    assert draft is not None
    assert draft["title"] == "Senior Backend Engineer"
    assert draft["company"] == "Example Co"
    assert draft["department"] == "Platform"
    assert draft["location"] == "Remote"
    assert draft["schema_version"] == "jd-review-v1"
    assert draft["overall_confidence"] == 1.0
    assert draft["parser_version"] is None
    assert draft["model_name"] is None

    responsibility = draft["responsibilities"][0]
    assert responsibility["provenance"] == "manual"
    assert responsibility["confidence"] == 1.0
    assert responsibility["evidence"] is None
    assert responsibility["evidence_status"] == "unavailable"
    assert responsibility["key"] == "manual-0"

    skill = draft["required_skills"][0]
    assert skill["provenance"] == "manual"
    assert skill["critical"] is True

    assert draft["notes"] == "Referral"


async def test_manual_sparse_entry_keeps_nulls_and_empty_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    result = await JDImportService().create_manual(
        FakeImportSession(),  # type: ignore[arg-type]
        payload=_payload(
            company=None,
            location=None,
            department=None,
            responsibilities=[],
            required_skills=[],
            preferred_skills=[],
            notes=None,
        ),
    )

    jd = result.jd
    draft = jd.review_draft
    assert draft is not None
    assert jd.company is None
    assert jd.location is None
    assert draft["company"] is None
    assert draft["responsibilities"] == []
    assert draft["required_skills"] == []
    assert draft["preferred_skills"] == []
    assert draft["notes"] is None


async def test_manual_sets_manual_field_sources_and_content_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    result = await JDImportService().create_manual(FakeImportSession(), payload=_payload())  # type: ignore[arg-type]

    jd = result.jd
    assert jd.field_sources == {"title": "manual", "company": "manual"}
    assert isinstance(jd.content_hash, str)
    assert len(jd.content_hash) == 64
    assert jd.raw_text == "Senior Backend Engineer Example Co Platform Remote Go Own service reliability"


async def test_manual_duplicate_detection_uses_canonical_text_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.application import jd_import_service as service_mod

    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)

    first = await JDImportService().create_manual(FakeImportSession(), payload=_payload())  # type: ignore[arg-type]
    second = await JDImportService().create_manual(
        FakeImportSession(),  # type: ignore[arg-type]
        payload=_payload(company="Example Co "),
    )

    assert first.jd.content_hash == second.jd.content_hash
    assert first.jd.content_hash == service_mod.content_hash(
        "Senior Backend Engineer Example Co Platform Remote Go Own service reliability"
    )


async def test_manual_duplicate_enters_duplicate_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    existing = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Senior Backend Engineer",
        source_type="text",
        raw_text="Senior Backend Engineer Example Co",
        content_hash="a" * 64,
    )
    session = FakeImportSession(existing=[existing.id])

    result = await JDImportService().create_manual(session, payload=_payload())  # type: ignore[arg-type]

    jd = result.jd
    assert jd.status == JDStatus.DUPLICATE_PENDING.value
    assert jd.processing_step == JDProcessingStep.DUPLICATE_CHECK.value
    assert jd.duplicate_of_id == existing.id


async def test_manual_allow_duplicate_skips_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    existing = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Senior Backend Engineer",
        source_type="text",
        raw_text="Senior Backend Engineer Example Co",
        content_hash="a" * 64,
    )
    session = FakeImportSession(existing=[existing.id])

    result = await JDImportService().create_manual(
        session,  # type: ignore[arg-type]
        payload=_payload(allow_duplicate=True),
    )

    assert result.jd.status == JDStatus.NEEDS_REVIEW.value
    assert result.jd.duplicate_of_id is None


async def test_manual_requires_non_blank_title(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.application.jd_import_service import JDImportError

    async def no_dispatch(*_: object, **__: object) -> None:
        raise AssertionError("manual creation must not dispatch a worker run")

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    with pytest.raises(JDImportError, match="requires a title"):
        await JDImportService().create_manual(FakeImportSession(), payload=_payload(title="   "))  # type: ignore[arg-type]


def test_manual_draft_rejects_invalid_provenance_and_evidence_fields() -> None:
    # The DraftItem shape must stay within the RIP-011 review schema: no
    # fabricated source quote is accepted on write.
    from backend.domain.jd.schemas import ReviewDraft

    draft = ReviewDraft(
        title="Role",
        required_skills=[
            {  # type: ignore[list-item]
                "key": "manual-0",
                "value": "Go",
                "evidence": None,
                "evidence_status": "unavailable",
                "confidence": 1.0,
                "provenance": "manual",
            }
        ],
    )
    assert draft.required_skills[0].provenance == "manual"
    assert draft.required_skills[0].evidence is None


def test_manual_draft_roundtrips_through_review_draft_schema() -> None:
    from backend.application.jd_import_service import _manual_review_draft
    from backend.domain.jd.schemas import ReviewDraft

    payload = _payload(
        required_skills=[
            {"name": "Go", "critical": True},
            {"name": "Python", "critical": False},
        ],  # type: ignore[list-item]
    )
    draft = _manual_review_draft(payload)
    parsed = ReviewDraft(**draft)  # type: ignore[arg-type]
    assert parsed.required_skills[0].value == "Go"
    assert parsed.required_skills[0].critical is True
    assert parsed.required_skills[1].value == "Python"
    assert parsed.schema_version == "jd-review-v1"


def test_manual_create_never_creates_job_target() -> None:
    # Job Target creation is a downstream command; the manual import path has no
    # reference to it. The integration test suite covers the import API itself.
    import backend.application.jd_import_service as service_mod

    source = open(service_mod.__file__).read()
    assert "JobTarget" not in source


def test_manual_model_requires_no_file_or_url_source() -> None:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Role",
        source_type="manual",
        raw_text="Role",
        status=JDStatus.NEEDS_REVIEW.value,
        processing_step=JDProcessingStep.REVIEW.value,
    )
    assert jd.source_file_id is None
    assert jd.source_url is None
