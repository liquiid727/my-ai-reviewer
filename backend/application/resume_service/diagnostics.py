"""Safe, stable diagnostics for the resume processing workflow.

The worker may see provider payloads, prompts, or parser exceptions. This
module is the single boundary that turns those internal failures into a small
allow-listed record suitable for persistence and API responses.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

RESUME_PROCESSING_TIMEOUT = "RESUME_PROCESSING_TIMEOUT"
RESUME_LLM_REQUEST_TIMEOUT = "RESUME_LLM_REQUEST_TIMEOUT"
RESUME_PIPELINE_DISPATCH_FAILED = "RESUME_PIPELINE_DISPATCH_FAILED"
RESUME_PRIVACY_EXPIRED = "RESUME_PRIVACY_EXPIRED"
RESUME_PROCESSING_FAILED = "RESUME_PROCESSING_FAILED"

SAFE_MESSAGES: dict[str, str] = {
    RESUME_PROCESSING_TIMEOUT: "Resume processing timed out. Please retry.",
    RESUME_LLM_REQUEST_TIMEOUT: "The AI service took too long to respond. Please retry.",
    RESUME_PIPELINE_DISPATCH_FAILED: "Processing could not be started. Please retry later.",
    RESUME_PRIVACY_EXPIRED: "Privacy review expired; upload the resume again.",
    RESUME_PROCESSING_FAILED: "Resume processing failed. Please retry.",
}

_KNOWN_CODES = frozenset(SAFE_MESSAGES)


def public_error_message(error_code: str) -> str:
    """Return a user-safe message for a known code."""

    return SAFE_MESSAGES.get(error_code, SAFE_MESSAGES[RESUME_PROCESSING_FAILED])


def error_code_for_exception(error: BaseException) -> str:
    """Map an internal exception to a stable, non-sensitive error code."""

    name = type(error).__name__.lower()
    if "timeout" in name or "timelimit" in name:
        return RESUME_LLM_REQUEST_TIMEOUT
    return RESUME_PROCESSING_FAILED


def build_failure_details(
    error_code: str,
    *,
    step: str | None = None,
    attempt: int | None = None,
    retryable: bool = False,
    task_id: str | None = None,
    public_message: str | None = None,
) -> dict[str, Any]:
    """Build the allow-listed internal/public diagnostic payload."""

    code = error_code if error_code in _KNOWN_CODES else RESUME_PROCESSING_FAILED
    details: dict[str, Any] = {
        "error_code": code,
        "public_message": public_message or public_error_message(code),
        "retryable": retryable,
    }
    if step:
        details["step"] = step
    if attempt is not None:
        details["attempt"] = max(1, int(attempt))
    if task_id:
        details["task_id"] = task_id
    return details


def normalize_failure_details(
    details: Mapping[str, Any] | None,
    legacy_error: str | None = None,
) -> dict[str, Any] | None:
    """Normalize new details and old persisted errors to the safe contract."""

    if details:
        code = str(details.get("error_code", RESUME_PROCESSING_FAILED))
        if code not in _KNOWN_CODES:
            code = RESUME_PROCESSING_FAILED
        return build_failure_details(
            code,
            step=_safe_string(details.get("step")),
            attempt=_safe_int(details.get("attempt")),
            retryable=bool(details.get("retryable", False)),
            public_message=public_error_message(code),
        )

    if not legacy_error:
        return None

    legacy_lower = legacy_error.lower()
    if "softtimelimitexceeded" in legacy_lower or "timelimit" in legacy_lower:
        code = RESUME_PROCESSING_TIMEOUT
    elif "privacy review expired" in legacy_lower:
        code = RESUME_PRIVACY_EXPIRED
    elif "dispatch" in legacy_lower and "failed" in legacy_lower:
        code = RESUME_PIPELINE_DISPATCH_FAILED
    else:
        code = RESUME_PROCESSING_FAILED
    return build_failure_details(code, public_message=public_error_message(code))


def _safe_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return max(1, value)
    return None


__all__ = [
    "RESUME_LLM_REQUEST_TIMEOUT",
    "RESUME_PIPELINE_DISPATCH_FAILED",
    "RESUME_PRIVACY_EXPIRED",
    "RESUME_PROCESSING_FAILED",
    "RESUME_PROCESSING_TIMEOUT",
    "build_failure_details",
    "error_code_for_exception",
    "normalize_failure_details",
    "public_error_message",
]
