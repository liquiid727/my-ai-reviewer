"""Legacy privacy remediation helpers used by the explicit migration command."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.domain.privacy.redactor import PrivacyGuard, ResumePrivacyRedactor


def scrub_payload(payload: Any) -> tuple[Any, dict[str, Any]]:
    """Return a recursively masked copy and a safe manifest.

    This helper never returns the source value in the manifest. It is used by
    the remediation command before deleting unsafe historical rows/objects.
    """
    redactor = ResumePrivacyRedactor()
    counters: dict[str, int] = defaultdict(int)
    placeholders: list[dict[str, Any]] = []

    def scrub(value: Any) -> Any:
        if isinstance(value, str):
            result = redactor.redact(value)
            masked = result.masked_text
            for placeholder in result.manifest.placeholders:
                counters[placeholder.entity_type] += 1
                prefix = "ORG" if placeholder.entity_type == "organization" else placeholder.entity_type.upper()
                token = f"[[{prefix}_{counters[placeholder.entity_type]:02d}]]"
                masked = masked.replace(placeholder.token, token)
                placeholders.append(placeholder.model_copy(update={"token": token}).model_dump(mode="json"))
            return masked
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()}
        return value

    masked = scrub(payload)
    PrivacyGuard().assert_masked(masked)
    return masked, {"placeholders": placeholders, "policy_version": "resume-privacy-v1"}
