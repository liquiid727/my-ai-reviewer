"""Local resume redaction and transient export hydration."""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from backend.domain.privacy.schemas import (
    PrivacyManifest,
    PrivacyPlaceholder,
    RedactionResult,
)

TOKEN_RE = re.compile(r"\[\[[A-Z]+_\d{2,}\]\]")
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.IGNORECASE)


class PrivacyViolationError(ValueError):
    """Raised when clear sensitive data crosses a masked-data boundary."""


class UnknownPrivacyPlaceholderError(ValueError):
    """Raised without including a submitted replacement value."""


@dataclass(frozen=True)
class _Finding:
    value: str
    entity_type: str
    detector: str


_PATTERNS: tuple[tuple[str, str, re.Pattern[str], str | None], ...] = (
    (
        "email",
        "regex.email",
        re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE),
        None,
    ),
    (
        "url",
        "regex.url",
        re.compile(r"(?:https?://|www\.)[^\s<>()]+", re.IGNORECASE),
        None,
    ),
    (
        "phone",
        "regex.phone",
        re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)|(?<!\d)\+?\d[\d ()-]{8,}\d(?!\d)"),
        None,
    ),
    (
        "account",
        "regex.id",
        re.compile(r"(?<![0-9A-Z])\d{17}[0-9Xx](?![0-9A-Z])"),
        None,
    ),
    (
        "address",
        "layout.address",
        re.compile(r"(?:地址|住址|Address)\s*[:：]\s*(?P<value>[^\n]{4,80})", re.IGNORECASE),
        "value",
    ),
    (
        "school",
        "regex.school",
        re.compile(
            r"(?P<value>[\u4e00-\u9fffA-Za-z0-9·&()（） -]{2,40}"
            r"(?:大学|学院|学校|University|College))",
            re.IGNORECASE,
        ),
        "value",
    ),
    (
        "organization",
        "regex.organization",
        re.compile(
            r"(?P<value>[\u4e00-\u9fffA-Za-z0-9·&()（） -]{2,50}"
            r"(?:有限责任公司|有限公司|集团|公司|研究院|实验室|\bInc\.?|\bLtd\.?|\bLLC|\bCorp\.?))",
            re.IGNORECASE,
        ),
        "value",
    ),
    (
        "project",
        "layout.project",
        re.compile(r"(?:项目名称|项目|Project)\s*[:：]\s*(?P<value>[^\n,，;；]{2,50})", re.IGNORECASE),
        "value",
    ),
    (
        "person",
        "layout.person",
        re.compile(
            r"(?:姓名|联系人|Name)\s*[:：]\s*"
            r"(?P<value>[\u4e00-\u9fff·]{2,6}|[A-Za-z][A-Za-z .'-]{1,50})",
            re.IGNORECASE,
        ),
        "value",
    ),
)


def _clean_value(value: str) -> str:
    return value.strip().rstrip(".,，。;；")


def _first_line_person(text: str) -> _Finding | None:
    for raw_line in text.splitlines()[:4]:
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff·]{2,4}", line):
            return _Finding(line, "person", "layout.first-line")
        if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,50}", line) and len(line.split()) <= 4:
            return _Finding(line, "person", "layout.first-line")
        break
    return None


class ResumePrivacyRedactor:
    """High-recall local redactor for Chinese and English resume text."""

    def redact(self, text: str) -> RedactionResult:
        findings: list[_Finding] = []
        first_person = _first_line_person(text)
        if first_person is not None:
            findings.append(first_person)

        for entity_type, detector, pattern, group in _PATTERNS:
            for match in pattern.finditer(text):
                value = _clean_value(match.group(group) if group else match.group(0))
                if value and not TOKEN_RE.fullmatch(value):
                    findings.append(_Finding(value, entity_type, detector))

        # De-duplicate normalized values, preferring the more specific entity type found first.
        unique: dict[str, _Finding] = {}
        for finding in findings:
            key = finding.value.casefold()
            unique.setdefault(key, finding)

        counters: dict[str, int] = defaultdict(int)
        tokens: dict[str, str] = {}
        for key, finding in unique.items():
            counters[finding.entity_type] += 1
            prefix = "ORG" if finding.entity_type == "organization" else finding.entity_type.upper()
            tokens[key] = f"[[{prefix}_{counters[finding.entity_type]:02d}]]"

        masked = text
        # Longest first prevents a short finding from corrupting a wider one.
        for key, finding in sorted(unique.items(), key=lambda item: len(item[1].value), reverse=True):
            masked = re.sub(re.escape(finding.value), tokens[key], masked, flags=re.IGNORECASE)

        placeholders: list[PrivacyPlaceholder] = []
        for key, finding in unique.items():
            token = tokens[key]
            occurrence_count = masked.count(token)
            index = masked.find(token)
            context = masked[max(0, index - 24): index + len(token) + 24] if index >= 0 else ""
            placeholders.append(PrivacyPlaceholder(
                token=token,
                entity_type=finding.entity_type,
                occurrence_count=max(1, occurrence_count),
                context=context,
                detector=finding.detector,
            ))

        return RedactionResult(
            masked_text=masked,
            manifest=PrivacyManifest(placeholders=placeholders),
        )


class PrivacyGuard:
    """Fail closed for direct identifiers at any resume-derived LLM boundary."""

    _direct_patterns = tuple(pattern for kind, _, pattern, _ in _PATTERNS if kind in {
        "email", "url", "phone", "account", "address",
    })

    def assert_masked(self, payload: Any) -> None:
        import json

        serialized = json.dumps(payload, ensure_ascii=False, default=str)
        # Stable internal ids are not contact data and may contain digit/hyphen
        # sequences that resemble a loosely formatted phone number.
        without_tokens = UUID_RE.sub("", TOKEN_RE.sub("", serialized))
        if any(pattern.search(without_tokens) for pattern in self._direct_patterns):
            raise PrivacyViolationError("Resume-derived payload contains unmasked sensitive data")


def apply_privacy_replacements(
    value: Any,
    replacements: dict[str, str],
    *,
    allowed_tokens: set[str],
) -> Any:
    """Return a deep hydrated copy, accepting only manifest-declared exact tokens."""
    unknown = set(replacements) - allowed_tokens
    if unknown:
        raise UnknownPrivacyPlaceholderError("Unknown privacy placeholder")
    if any(not TOKEN_RE.fullmatch(token) for token in replacements):
        raise UnknownPrivacyPlaceholderError("Invalid privacy placeholder")

    cloned = copy.deepcopy(value)

    def hydrate(item: Any) -> Any:
        if isinstance(item, str):
            result = item
            for token, replacement in replacements.items():
                result = result.replace(token, replacement)
            return result
        if isinstance(item, list):
            return [hydrate(child) for child in item]
        if isinstance(item, dict):
            return {key: hydrate(child) for key, child in item.items()}
        return item

    return hydrate(cloned)


def apply_manual_mask_spans(
    text: str,
    spans: list[tuple[int, int, str]],
    *,
    existing_manifest: PrivacyManifest | None,
) -> RedactionResult:
    """Apply user-confirmed character spans without retaining selected source values."""
    allowed_types = {
        "person", "phone", "email", "address", "account", "url",
        "organization", "school", "project", "photo",
    }
    ordered = sorted(spans, key=lambda item: item[0], reverse=True)
    previous_start = len(text) + 1
    counters: dict[str, int] = defaultdict(int)
    placeholders = list(existing_manifest.placeholders) if existing_manifest else []
    for placeholder in placeholders:
        counters[placeholder.entity_type] += 1

    masked = text
    allocated: list[PrivacyPlaceholder] = []
    for start, end, entity_type in ordered:
        if entity_type not in allowed_types or start < 0 or end <= start or end > len(text):
            raise ValueError("Invalid manual privacy span")
        if end > previous_start:
            raise ValueError("Manual privacy spans overlap")
        selected = text[start:end]
        if TOKEN_RE.search(selected):
            raise ValueError("Manual privacy span overlaps an existing placeholder")
        counters[entity_type] += 1
        prefix = "ORG" if entity_type == "organization" else entity_type.upper()
        token = f"[[{prefix}_{counters[entity_type]:02d}]]"
        masked = masked[:start] + token + masked[end:]
        allocated.append(PrivacyPlaceholder(
            token=token,
            entity_type=entity_type,
            occurrence_count=1,
            context="",
            detector="manual.review",
        ))
        previous_start = start

    for placeholder in allocated:
        index = masked.find(placeholder.token)
        placeholder.context = masked[max(0, index - 24):index + len(placeholder.token) + 24]
    placeholders.extend(reversed(allocated))
    return RedactionResult(
        masked_text=masked,
        manifest=PrivacyManifest(
            placeholders=placeholders,
            risk_flags=list(existing_manifest.risk_flags) if existing_manifest else [],
        ),
    )
