"""Interview Scenario read-only API (AIP-013 §9)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.v1.schemas import APIResponse
from backend.domain.interview_scenario.registry import (
    ScenarioNotFoundError,
    ScenarioRegistry,
    ScenarioVersionNotFoundError,
    get_registry,
)
from backend.domain.interview_scenario.schemas import InterviewScenario, InterviewScenarioSummary

router = APIRouter(prefix="/interview-scenarios", tags=["interview-scenarios"])


def _public_detail(scenario: InterviewScenario) -> dict[str, object]:
    return {
        "key": scenario.key,
        "version": scenario.version,
        "name_key": scenario.name_key,
        "description_key": scenario.description_key,
        "mode": scenario.mode,
        "stages": [
            {
                "stage": s.stage.value,
                "weight": s.weight,
                "coverage_categories": [c.value for c in s.coverage_categories],
                "allows_candidate_questions": s.allows_candidate_questions,
            }
            for s in scenario.stages
        ],
        "durations": [
            {
                "duration": b.duration.value,
                "main_questions": b.main_questions,
                "total_followups": b.total_followups,
                "max_followup_depth": b.max_followup_depth,
                "skip_allowance": b.skip_allowance,
            }
            for b in scenario.durations
        ],
        "allowed_coverage_categories": [c.value for c in scenario.allowed_coverage_categories],
        "allowed_difficulties": [d.value for d in scenario.allowed_difficulties],
        "allowed_languages": [lang.value for lang in scenario.allowed_languages],
        "candidate_questions_min": scenario.candidate_questions_min,
        "candidate_questions_max": scenario.candidate_questions_max,
        "scoring": {
            "dimensions": scenario.scoring.dimensions,
            "prompt_policy_version": scenario.scoring.prompt_policy_version,
        },
    }


def _summary_payload(summary: InterviewScenarioSummary) -> dict[str, object]:
    return {
        "key": summary.key,
        "version": summary.version,
        "name_key": summary.name_key,
        "description_key": summary.description_key,
        "stage_keys": summary.stage_keys,
        "main_emphasis": summary.main_emphasis,
    }


def _scenario_registry() -> ScenarioRegistry:
    return get_registry()


@router.get("")
def list_scenarios() -> APIResponse:
    """List active scenario summaries and allowed global options."""
    reg = _scenario_registry()
    summaries = reg.list_active()
    data = {
        "scenarios": [_summary_payload(s) for s in summaries],
        "allowed_global_options": {
            "durations": [15, 30, 45, 60],
            "difficulties": ["basic", "standard", "challenge"],
            "languages": ["zh-CN", "en"],
            "max_followup_depth": 2,
        },
    }
    return APIResponse(data=data)


@router.get("/{key}")
def get_scenario(key: str, version: int | None = None) -> APIResponse:
    """Return current or exact-version public scenario detail."""
    reg = _scenario_registry()
    try:
        scenario = reg.get(key, version)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ScenarioVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIResponse(data=_public_detail(scenario))
