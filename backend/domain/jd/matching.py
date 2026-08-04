"""JD matching pure rules (no I/O).

Stateful match + persistence lives in ``backend.application.jd_service.matching``.
"""

from __future__ import annotations

from backend.domain.jd.policies import (
    _compute_match,
    compute_match,
    norm_skill,
)

__all__ = [
    "_compute_match",
    "compute_match",
    "norm_skill",
]
