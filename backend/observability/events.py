"""Structured, PII-safe resume processing events."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.observability.context import resume_context

logger = logging.getLogger("backend.resume_processing")


def emit_resume_event(
    event: str,
    *,
    resource_id: str | None,
    run_id: str | None = None,
    task_id: str | None = None,
    step: str | None = None,
    attempt: int | None = None,
    status: str | None = None,
    error_code: str | None = None,
    retryable: bool | None = None,
    duration_ms: int | None = None,
    level: int = logging.INFO,
    **extra: Any,
) -> None:
    """Emit one JSON line with an allow-listed correlation envelope."""

    context = resume_context()
    payload: dict[str, Any] = {
        "event": event,
        "resource_type": "resume",
        "resource_id": resource_id or context.get("resource_id", "unknown"),
        "run_id": run_id or context.get("run_id"),
        "task_id": task_id or context.get("task_id"),
        "step": step or context.get("step"),
        "attempt": attempt if attempt is not None else context.get("attempt"),
        "status": status,
        "error_code": error_code,
        "retryable": retryable,
        "duration_ms": duration_ms,
    }
    payload.update({key: value for key, value in extra.items() if value is not None})
    payload = {key: value for key, value in payload.items() if value is not None}
    logger.log(level, "resume_event %s", json.dumps(payload, sort_keys=True, separators=(",", ":")))
