"""Resume privacy domain API."""

from backend.domain.privacy.redactor import (
    PrivacyGuard,
    PrivacyViolationError,
    ResumePrivacyRedactor,
    UnknownPrivacyPlaceholderError,
    apply_manual_mask_spans,
    apply_privacy_replacements,
)
from backend.domain.privacy.schemas import PrivacyManifest, PrivacyPlaceholder, RedactionResult

__all__ = [
    "PrivacyGuard",
    "PrivacyManifest",
    "PrivacyPlaceholder",
    "PrivacyViolationError",
    "RedactionResult",
    "ResumePrivacyRedactor",
    "UnknownPrivacyPlaceholderError",
    "apply_privacy_replacements",
    "apply_manual_mask_spans",
]
