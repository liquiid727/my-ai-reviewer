"""Shared fingerprint freshness policy for JD match consumers."""

from __future__ import annotations

from typing import Any

from backend.domain.jd.matching_v2 import (
    HARD_FILTER_POLICY_VERSION,
    MATCH_PROMPT_VERSION,
    MATCH_SCHEMA_VERSION,
    MATCHER_VERSION,
    MatchMode,
    MatchStatus,
    StaleReason,
    build_input_fingerprint,
)


def current_match_fingerprint(
    *,
    jd: Any,
    profile: Any,
    facts_revision: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
) -> str:
    parts = fingerprint_parts(
        jd=jd,
        profile=profile,
        facts_revision=facts_revision,
        provider=provider,
        model_name=model_name,
    )
    return build_input_fingerprint(parts)


def fingerprint_parts(
    *,
    jd: Any,
    profile: Any,
    facts_revision: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
) -> dict[str, object]:
    return {
        "jd_id": str(getattr(jd, "id", "")),
        "jd_structured_revision": getattr(jd, "structured_revision", 1) or 1,
        "jd_content_hash": getattr(jd, "content_hash", None) or _bounded_hash(getattr(jd, "raw_text", "")),
        "resume_id": str(getattr(profile, "resume_id", "")),
        "profile_revision": _revision_from_profile(profile),
        "resume_facts_revision": facts_revision or "facts-v1",
        "matcher_version": MATCHER_VERSION,
        "hard_filter_policy_version": HARD_FILTER_POLICY_VERSION,
        "prompt_version": MATCH_PROMPT_VERSION,
        "schema_version": MATCH_SCHEMA_VERSION,
        "provider": provider,
        "model_name": model_name,
    }


def stale_reasons(
    match: Any,
    *,
    expected_fingerprint: str,
    provider: str | None = None,
    model_name: str | None = None,
) -> list[str]:
    reasons: list[StaleReason] = []
    if getattr(match, "status", None) != MatchStatus.READY.value:
        reasons.append(StaleReason.RESULT_FAILED_OR_INCOMPLETE)
    if getattr(match, "mode", None) != MatchMode.HYBRID_V2.value:
        reasons.append(StaleReason.MATCHER_VERSION_CHANGED)
    if getattr(match, "input_fingerprint", None) != expected_fingerprint:
        reasons.append(StaleReason.JD_REVISION_CHANGED)
    if getattr(match, "matcher_version", None) != MATCHER_VERSION:
        reasons.append(StaleReason.MATCHER_VERSION_CHANGED)
    if getattr(match, "hard_filter_policy_version", None) != HARD_FILTER_POLICY_VERSION:
        reasons.append(StaleReason.HARD_FILTER_POLICY_CHANGED)
    if (
        getattr(match, "prompt_version", None) != MATCH_PROMPT_VERSION
        or getattr(match, "schema_version", None) != MATCH_SCHEMA_VERSION
    ):
        reasons.append(StaleReason.PROMPT_OR_SCHEMA_CHANGED)
    if provider is not None and getattr(match, "provider", None) != provider:
        reasons.append(StaleReason.MODEL_CHANGED)
    if model_name is not None and getattr(match, "model_name", None) != model_name:
        reasons.append(StaleReason.MODEL_CHANGED)
    return [reason.value for reason in dict.fromkeys(reasons)]


def is_fresh(
    match: Any,
    *,
    expected_fingerprint: str,
    provider: str | None = None,
    model_name: str | None = None,
) -> bool:
    return not stale_reasons(match, expected_fingerprint=expected_fingerprint, provider=provider, model_name=model_name)


def _revision_from_profile(profile: Any) -> str:
    parser_version = getattr(profile, "parser_version", None)
    updated_at = getattr(profile, "updated_at", None)
    if updated_at is not None and hasattr(updated_at, "isoformat"):
        isoformat = updated_at.isoformat
        return f"{parser_version or 'profile-v1'}:{isoformat()}"
    return f"{parser_version or 'profile-v1'}:{updated_at}"


def _bounded_hash(value: object) -> str:
    import hashlib

    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


__all__ = ["current_match_fingerprint", "fingerprint_parts", "is_fresh", "stale_reasons"]
