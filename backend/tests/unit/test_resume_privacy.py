"""RIP-009 privacy-domain contracts."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest

from backend.domain.privacy import (
    PrivacyGuard,
    PrivacyViolationError,
    ResumePrivacyRedactor,
    UnknownPrivacyPlaceholderError,
    apply_manual_mask_spans,
    apply_privacy_replacements,
)

SENSITIVE_TEXT = """张三
电话：13800138000
邮箱：zhangsan@example.com
地址：上海市浦东新区世纪大道 100 号
工作经历
字节跳动有限公司 后端工程师
教育经历
清华大学 计算机硕士
项目名称：飞舟平台
主页：https://example.com/zhangsan
"""


def test_redactor_masks_bilingual_resume_entities_without_manifest_cleartext() -> None:
    result = ResumePrivacyRedactor().redact(SENSITIVE_TEXT)

    for original in (
        "张三",
        "13800138000",
        "zhangsan@example.com",
        "上海市浦东新区世纪大道 100 号",
        "字节跳动有限公司",
        "清华大学",
        "飞舟平台",
        "https://example.com/zhangsan",
    ):
        assert original not in result.masked_text
        assert original not in json.dumps(result.manifest.model_dump(), ensure_ascii=False)

    tokens = {item.entity_type: item.token for item in result.manifest.placeholders}
    assert tokens["person"] == "[[PERSON_01]]"
    assert tokens["phone"] == "[[PHONE_01]]"
    assert tokens["email"] == "[[EMAIL_01]]"
    assert tokens["organization"] == "[[ORG_01]]"
    assert tokens["school"] == "[[SCHOOL_01]]"
    assert tokens["project"] == "[[PROJECT_01]]"


def test_repeated_entity_uses_one_stable_placeholder() -> None:
    result = ResumePrivacyRedactor().redact("张三负责平台。联系人：张三。")

    assert result.masked_text.count("[[PERSON_01]]") == 2
    assert len(result.manifest.placeholders) == 1
    assert result.manifest.placeholders[0].occurrence_count == 2


def test_privacy_guard_allows_tokens_and_blocks_clear_contact_data() -> None:
    guard = PrivacyGuard()
    guard.assert_masked({"identity": {"name": "[[PERSON_01]]", "phone": "[[PHONE_01]]"}})

    with pytest.raises(PrivacyViolationError):
        guard.assert_masked({"summary": "Call me on 13800138000"})


def test_partial_export_replacements_leave_missing_tokens_masked() -> None:
    payload: dict[str, Any] = {
        "identity": {"name": "[[PERSON_01]]", "phone": "[[PHONE_01]]"},
        "sections": [{"heading": "[[ORG_01]]", "bullets": ["Built APIs"]}],
    }
    hydrated = apply_privacy_replacements(
        payload,
        {"[[PERSON_01]]": "张三"},
        allowed_tokens={"[[PERSON_01]]", "[[PHONE_01]]", "[[ORG_01]]"},
    )

    hydrated_map = cast(dict[str, Any], hydrated)
    assert hydrated_map["identity"] == {"name": "张三", "phone": "[[PHONE_01]]"}
    sections = cast(list[dict[str, Any]], hydrated_map["sections"])
    assert sections[0]["heading"] == "[[ORG_01]]"
    assert payload["identity"]["name"] == "[[PERSON_01]]"


def test_export_rejects_unknown_placeholder_without_echoing_value() -> None:
    with pytest.raises(UnknownPrivacyPlaceholderError) as exc_info:
        apply_privacy_replacements(
            {"name": "[[PERSON_01]]"},
            {"[[UNKNOWN_01]]": "very-secret-value"},
            allowed_tokens={"[[PERSON_01]]"},
        )

    assert "very-secret-value" not in str(exc_info.value)


def test_manual_mask_span_allocates_token_without_storing_selected_value() -> None:
    text = "工作经历：秘密客户平台，负责 API。"
    start = text.index("秘密客户平台")

    result = apply_manual_mask_spans(
        text,
        [(start, start + len("秘密客户平台"), "project")],
        existing_manifest=None,
    )

    assert result.masked_text == "工作经历：[[PROJECT_01]]，负责 API。"
    assert "秘密客户平台" not in json.dumps(result.manifest.model_dump(), ensure_ascii=False)


def test_manual_mask_span_rejects_existing_placeholder_overlap() -> None:
    text = "姓名：[[PERSON_01]]"
    start = text.index("[[PERSON_01]]")

    with pytest.raises(ValueError):
        apply_manual_mask_spans(
            text,
            [(start, start + len("[[PERSON_01]]"), "person")],
            existing_manifest=None,
        )
