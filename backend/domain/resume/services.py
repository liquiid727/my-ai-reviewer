"""Resume domain surface.

Pipeline orchestration lives in ``backend.application.resume_service.pipeline``.
This module keeps pure helpers and intentional compatibility names that do not
pull application/infrastructure dependencies.
"""

from __future__ import annotations

from backend.domain.resume.policies import (
    build_reparse_history_payload,
    merge_classification_into_profile,
)

__all__ = [
    "build_reparse_history_payload",
    "merge_classification_into_profile",
]
