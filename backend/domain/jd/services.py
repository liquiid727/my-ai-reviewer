"""JD domain surface.

Processing orchestration lives in ``backend.application.jd_service.processing``.
This module keeps pure helpers and compatibility names without I/O.
"""

from __future__ import annotations

from backend.domain.jd.policies import (
    JDProcessingError,
    content_hash,
    extraction_values,
    merged_extraction_values,
    normalize_jd_text,
)

__all__ = [
    "JDProcessingError",
    "content_hash",
    "extraction_values",
    "merged_extraction_values",
    "normalize_jd_text",
]
