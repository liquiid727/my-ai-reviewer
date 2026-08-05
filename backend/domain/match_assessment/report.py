"""Match Assessment report projection rules (RIP-014 §6.1, §6.3).

The report is a read-only projection over a completed assessment, its
immutable version snapshots, and current-target advisory metadata. It is
never stored and never mutates the assessment. All rule functions here are
pure: they take plain model-agnostic dicts/lists and return the report
sections the API embeds on the completed detail payload.

Action eligibility is informational only — low scores never disable
downstream actions. Route identifiers are stable API/route paths; the UI
resolves them, never the report.
"""

from __future__ import annotations

from typing import Any

GAP_CLASS_ORDER: tuple[str, ...] = (
    "capability_gap",
    "expression_gap",
    "evidence_gap",
    "hard_constraint_risk",
)

ACTION_TYPES: dict[str, str] = {
    "capability_gap": "screen",
    "expression_gap": "review",
    "evidence_gap": "probe",
    "hard_constraint_risk": "screen",
}

# Action identifiers and their stable route hints (RIP-014 §6.3).
RESUME_OPTIMIZATION_ROUTE = "/builder/:draftId"
PLAN_ROUTE = "/api/v1/plans"
INTERVIEW_ROUTE = "/api/v1/interview/create"


def gap_class_counts(gaps: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts per primary gap class plus severity and action breakdowns."""
    classes = {key: 0 for key in GAP_CLASS_ORDER}
    severities: dict[str, int] = {}
    actions: dict[str, int] = {}
    for gap in gaps:
        category = gap.get("category", "evidence_gap")
        if category in classes:
            classes[category] += 1
        severity = gap.get("severity")
        if severity is not None:
            severities[str(severity)] = severities.get(str(severity), 0) + 1
        action = gap.get("action_type") or ACTION_TYPES.get(category, "review")
        actions[str(action)] = actions.get(str(action), 0) + 1
    return {
        "counts_by_class": classes,
        "counts_by_severity": severities,
        "counts_by_action_type": actions,
    }


def _cited_evidence_ids(dimensions: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for dimension in dimensions:
        for key in ("cited_jd_evidence", "cited_resume_evidence"):
            for item in dimension.get(key) or []:
                if isinstance(item, str) and item not in ids:
                    ids.append(item)
    return ids


def evidence_sufficiency(
    evidence_summary: dict[str, Any],
    dimensions: list[dict[str, Any]],
    catalog_ids: set[str],
) -> dict[str, Any]:
    """Evidence counts plus citations that the Source Catalog never offered.

    A citation outside the catalog is an explicit unknown: the assessment
    cannot be reproduced from its own pinned inputs.
    """
    cited = _cited_evidence_ids(dimensions)
    unknown = [item for item in cited if item not in catalog_ids]
    return {
        "jd_evidence": int(evidence_summary.get("jd_evidence") or 0),
        "resume_evidence": int(evidence_summary.get("resume_evidence") or 0),
        "cited_ids": cited,
        "unknown_citations": unknown,
    }


def stale_versions(
    *,
    jd_version_id: str | None,
    resume_version_id: str | None,
    current_jd_version_id: str | None,
    target_default_jd_version_id: str | None,
    target_default_resume_version_id: str | None,
) -> dict[str, Any]:
    """Advisory staleness against *current* versions; never replaces inputs.

    A report becomes stale when the JD moved to a newer published version or
    the target's default versions moved on. The assessment itself is
    immutable and is always returned as evaluated.
    """
    jd_flags: list[str] = []
    if (
        jd_version_id is not None
        and current_jd_version_id is not None
        and jd_version_id != current_jd_version_id
    ):
        jd_flags.append("jd_has_newer_published_version")
    if (
        jd_version_id is not None
        and target_default_jd_version_id is not None
        and jd_version_id != target_default_jd_version_id
    ):
        jd_flags.append("target_default_jd_version_moved")
    resume_flags: list[str] = []
    if (
        resume_version_id is not None
        and target_default_resume_version_id is not None
        and resume_version_id != target_default_resume_version_id
    ):
        resume_flags.append("target_default_resume_version_moved")
    return {
        "jd": jd_flags,
        "resume": resume_flags,
        "is_stale": bool(jd_flags or resume_flags),
    }


def action_routes(
    *,
    resume_version_id: str,
    resume_version_source_type: str | None,
    parsed_resume_id: str | None,
    builder_draft_id: str | None,
) -> list[dict[str, Any]]:
    """Safe eligibility flags and route identifiers for downstream actions.

    Never gated on score: every completed assessment may feed interview and
    plan flows. Resume optimization is only eligible when the assessment's
    resume snapshot comes from a builder draft, because that flow mutates the
    draft.
    """
    actions: list[dict[str, Any]] = []
    if resume_version_source_type == "builder_draft" and builder_draft_id is not None:
        actions.append(
            {
                "id": "resume_optimization",
                "label": "Optimize resume for this JD",
                "eligible": True,
                "route": RESUME_OPTIMIZATION_ROUTE,
                "method": "navigate",
                "destination": {"draft_id": str(builder_draft_id)},
            }
        )
    if parsed_resume_id is not None:
        actions.append(
            {
                "id": "plan",
                "label": "Build a job-search plan",
                "eligible": True,
                "route": PLAN_ROUTE,
                "method": "POST",
                "destination": {"resume_id": str(parsed_resume_id)},
            }
        )
        actions.append(
            {
                "id": "interview",
                "label": "Run a mock interview",
                "eligible": True,
                "route": INTERVIEW_ROUTE,
                "method": "POST",
                "destination": {"resume_id": str(parsed_resume_id)},
            }
        )
    return actions
