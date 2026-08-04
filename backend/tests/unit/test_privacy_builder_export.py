"""Transient Builder export privacy contracts."""

from __future__ import annotations

from backend.domain.resume_builder.schemas import ResumeDraft
from backend.domain.resume_builder.services import hydrate_draft_for_export


def test_hydrated_export_draft_is_a_copy_and_keeps_missing_tokens_masked() -> None:
    draft = ResumeDraft(
        title="[[PERSON_01]] 的简历",
        identity={"name": "[[PERSON_01]]", "phone": "[[PHONE_01]]"},
    )

    hydrated = hydrate_draft_for_export(
        draft,
        {"[[PERSON_01]]": "张三"},
        allowed_tokens={"[[PERSON_01]]", "[[PHONE_01]]"},
    )

    assert hydrated.title == "张三 的简历"
    assert hydrated.identity["name"] == "张三"
    assert hydrated.identity["phone"] == "[[PHONE_01]]"
    assert draft.identity["name"] == "[[PERSON_01]]"
