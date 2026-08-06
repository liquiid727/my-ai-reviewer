"""JD matching application package."""

from backend.application.jd_matching.freshness import (
    current_match_fingerprint,
    fingerprint_parts,
    is_fresh,
    stale_reasons,
)
from backend.application.jd_matching.service import (
    HybridJDMatchingService,
    JDMatchingError,
    MatchRunResult,
    serialize_match_v2,
)

__all__ = [
    "HybridJDMatchingService",
    "JDMatchingError",
    "MatchRunResult",
    "current_match_fingerprint",
    "fingerprint_parts",
    "is_fresh",
    "serialize_match_v2",
    "stale_reasons",
]
