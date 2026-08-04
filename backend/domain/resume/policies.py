"""Pure resume domain policies — no sessions, SDKs, or adapters."""

from __future__ import annotations

from typing import Any


def build_reparse_history_payload(
    *,
    prior_parsed_result: dict[str, Any] | None,
    parser_version: str | None,
    status: str,
    snapshot_at_iso: str,
) -> dict[str, Any]:
    """Append a reparse snapshot and return the reset parsed_result shell.

    Snapshot omits nested history to avoid recursive growth. Caller owns
    persistence and status transitions.
    """
    prior = prior_parsed_result or {}
    history = list(prior.get("history", []))
    snapshot_payload = {k: v for k, v in prior.items() if k != "history"}
    if snapshot_payload or parser_version:
        history.append(
            {
                "snapshot_at": snapshot_at_iso,
                "parser_version": parser_version,
                "status": str(status),
                "parsed_result": snapshot_payload,
            }
        )
    return {"history": history}


def merge_classification_into_profile(
    *,
    profile_dump: dict[str, Any],
    tech_direction_tags: list[str],
    experience_level: str,
    industry_tags: list[str],
) -> dict[str, Any]:
    """Return profile dump with ability_tags rebuilt from classification."""
    updated = dict(profile_dump)
    updated["ability_tags"] = [
        *tech_direction_tags,
        experience_level,
        *industry_tags,
    ]
    return updated
