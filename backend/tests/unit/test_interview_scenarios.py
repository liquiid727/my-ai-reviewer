"""Interview Scenario registry unit tests (AIP-013 #116)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.domain.interview_scenario.enums import (
    DurationMinutes,
    ScenarioDifficulty,
    ScenarioLanguage,
    ScenarioStage,
)
from backend.domain.interview_scenario.fixtures import build_fixtures
from backend.domain.interview_scenario.registry import (
    ScenarioNotFoundError,
    ScenarioRegistry,
    ScenarioRegistryInvalidError,
    ScenarioVersionNotFoundError,
    get_registry,
)
from backend.domain.interview_scenario.schemas import (
    InterviewScenario,
    ScenarioDurationBudget,
    ScenarioScoring,
    ScenarioStageConfig,
)


def test_registry_has_seven_active_scenarios() -> None:
    reg = get_registry()
    summaries = reg.list_active()
    keys = [s.key for s in summaries]
    assert keys == [
        "comprehensive",
        "hr_screen",
        "technical_first",
        "project_deep_dive",
        "system_design",
        "behavioral",
        "manager_round",
    ]


def test_all_stage_weights_sum_to_100() -> None:
    reg = get_registry()
    for scenario in reg:
        total = sum(s.weight for s in scenario.stages)
        assert total == 100, f"{scenario.key}: weights sum {total}"


def test_all_stage_order_matches_architecture() -> None:
    expected: dict[str, list[str]] = {
        "comprehensive": ["introduction", "core_skills", "project", "system_design", "behavior", "candidate_questions"],
        "hr_screen": ["introduction", "background", "motivation", "behavior", "candidate_questions"],
        "technical_first": ["introduction", "core_skills", "problem_solving", "project", "candidate_questions"],
        "project_deep_dive": [
            "introduction",
            "project_context",
            "project_decisions",
            "tradeoffs",
            "outcomes",
            "candidate_questions",
        ],
        "system_design": [
            "clarification",
            "architecture",
            "data",
            "scaling",
            "reliability",
            "tradeoffs",
            "candidate_questions",
        ],
        "behavioral": ["introduction", "ownership", "collaboration", "conflict", "learning", "candidate_questions"],
        "manager_round": [
            "introduction",
            "prioritization",
            "leadership",
            "cross_functional",
            "growth",
            "candidate_questions",
        ],
    }
    reg = get_registry()
    for scenario in reg:
        actual = [s.stage.value for s in scenario.stages]
        assert actual == expected[scenario.key], f"{scenario.key}: {actual}"


def test_budgets_follow_global_policy() -> None:
    reg = get_registry()
    policy = {
        15: (3, 1, 1),
        30: (5, 3, 1),
        45: (7, 5, 2),
        60: (9, 7, 2),
    }
    for scenario in reg:
        for budget in scenario.durations:
            main, follow, skip = policy[budget.duration.value]
            assert budget.main_questions == main
            assert budget.total_followups == follow
            assert budget.skip_allowance == skip
            assert budget.max_followup_depth == 2


def test_difficulty_language_mode_constraints() -> None:
    reg = get_registry()
    for scenario in reg:
        assert scenario.allowed_difficulties == [
            ScenarioDifficulty.BASIC,
            ScenarioDifficulty.STANDARD,
            ScenarioDifficulty.CHALLENGE,
        ]
        assert scenario.allowed_languages == [ScenarioLanguage.ZH_CN, ScenarioLanguage.EN]
        assert scenario.mode == "text"


def test_candidate_question_bounds() -> None:
    reg = get_registry()
    for scenario in reg:
        assert 0 <= scenario.candidate_questions_min <= 3
        assert 0 <= scenario.candidate_questions_max <= 3
        assert scenario.candidate_questions_max >= scenario.candidate_questions_min
        # Every scenario includes the candidate_questions stage.
        assert any(s.stage == ScenarioStage.CANDIDATE_QUESTIONS for s in scenario.stages)


def test_scoring_keys_present() -> None:
    reg = get_registry()
    for scenario in reg:
        assert scenario.scoring.dimensions
        assert scenario.scoring.prompt_policy_version == "plan-v1"


def test_get_returns_active_and_exact_version() -> None:
    reg = get_registry()
    scenario = reg.get("comprehensive")
    assert scenario.version == 1
    v1 = reg.get("comprehensive", 1)
    assert v1 == scenario


def test_get_not_found() -> None:
    reg = get_registry()
    with pytest.raises(ScenarioNotFoundError):
        reg.get("nonexistent")
    with pytest.raises(ScenarioVersionNotFoundError):
        reg.get("comprehensive", 99)


def test_duplicate_key_version_rejected() -> None:
    base = build_fixtures()[0]
    dup = base.model_copy()
    with pytest.raises(ScenarioRegistryInvalidError):
        ScenarioRegistry([base, dup])


def test_invalid_weights_rejected() -> None:
    base = build_fixtures()[0]
    bad = base.model_copy(deep=True)
    bad.stages[0].weight = 50  # breaks the 100 total
    with pytest.raises(ScenarioRegistryInvalidError):
        ScenarioRegistry([bad])


def test_unknown_coverage_category_rejected() -> None:
    base = build_fixtures()[0]
    bad = base.model_copy(deep=True)
    bad.allowed_coverage_categories = []
    with pytest.raises(ScenarioRegistryInvalidError):
        ScenarioRegistry([bad])


def test_skip_allowance_over_global_rejected() -> None:
    base = build_fixtures()[0]
    bad = base.model_copy(deep=True)
    for budget in bad.durations:
        if budget.duration == DurationMinutes.MINUTES_15:
            budget.skip_allowance = 2  # global is 1 for 15
    with pytest.raises(ScenarioRegistryInvalidError):
        ScenarioRegistry([bad])


def test_schema_rejects_duplicate_stages() -> None:
    with pytest.raises(ValidationError):
        InterviewScenario(
            key="bad",
            version=1,
            name_key="bad.name",
            description_key="bad.desc",
            stages=[
                ScenarioStageConfig(stage=ScenarioStage.INTRODUCTION, weight=50),
                ScenarioStageConfig(stage=ScenarioStage.INTRODUCTION, weight=50),
            ],
            durations=[
                ScenarioDurationBudget(duration=DurationMinutes.MINUTES_30, main_questions=5, total_followups=3)
            ],
            allowed_coverage_categories=[],
            allowed_difficulties=[ScenarioDifficulty.STANDARD],
            allowed_languages=[ScenarioLanguage.EN],
            scoring=ScenarioScoring(dimensions=["x"], prompt_policy_version="plan-v1"),
        )


def test_schema_rejects_candidate_max_over_3() -> None:
    with pytest.raises(ValidationError):
        InterviewScenario(
            key="bad",
            version=1,
            name_key="bad.name",
            description_key="bad.desc",
            stages=[ScenarioStageConfig(stage=ScenarioStage.INTRODUCTION, weight=100)],
            durations=[
                ScenarioDurationBudget(duration=DurationMinutes.MINUTES_30, main_questions=5, total_followups=3)
            ],
            allowed_coverage_categories=[],
            allowed_difficulties=[ScenarioDifficulty.STANDARD],
            allowed_languages=[ScenarioLanguage.EN],
            candidate_questions_max=4,
            scoring=ScenarioScoring(dimensions=["x"], prompt_policy_version="plan-v1"),
        )


def test_no_private_fields_in_any_fixture() -> None:
    """Prompts/questions/signals/rubrics must be absent from scenario fixtures."""
    reg = get_registry()
    for scenario in reg:
        blob = scenario.model_dump(mode="json")
        # Prompt policy *version* is public metadata; actual prompt content is private.
        forbidden = (
            "prompts",
            "planned_questions",
            "questions",
            "signals",
            "rubric",
            "expected_answer",
            "ideal_response",
        )
        for key in blob:
            assert key not in forbidden, f"{scenario.key} leaks private field '{key}'"
        # Recursive scan for private keys in nested structures.
        def _scan(value) -> None:
            if isinstance(value, dict):
                for k, v in value.items():
                    assert k not in forbidden, f"{scenario.key} leaks private field '{k}'"
                    _scan(v)
            elif isinstance(value, list):
                for item in value:
                    _scan(item)

        _scan(blob)


def test_legacy_enums_untouched() -> None:
    from backend.domain.interview.enums import Difficulty, InterviewStatus, QuestionStage, Recommendation

    assert QuestionStage.BASIC.value == "basic"
    assert QuestionStage.PROJECT.value == "project"
    assert QuestionStage.ARCHITECTURE.value == "architecture"
    assert QuestionStage.BEHAVIOR.value == "behavior"
    assert Difficulty.EASY.value == "easy"
    assert InterviewStatus.PENDING.value == "pending"
    assert Recommendation.YES.value == "yes"
