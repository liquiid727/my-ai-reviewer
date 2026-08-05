"""Safe resume failure diagnostics never echo legacy exception text."""

from backend.application.resume_service.diagnostics import (
    RESUME_PROCESSING_TIMEOUT,
    normalize_failure_details,
)


def test_legacy_soft_time_limit_is_normalized_to_safe_timeout() -> None:
    details = normalize_failure_details(
        None,
        "Resume processing failed (SoftTimeLimitExceeded: secret prompt fragment)",
    )

    assert details is not None
    assert details["error_code"] == RESUME_PROCESSING_TIMEOUT
    assert "SoftTimeLimitExceeded" not in details["public_message"]
    assert "secret prompt" not in details["public_message"]


def test_unknown_persisted_error_code_is_generic() -> None:
    details = normalize_failure_details({"error_code": "provider_payload"})

    assert details is not None
    assert details["error_code"] == "RESUME_PROCESSING_FAILED"
    assert "provider_payload" not in details["public_message"]
