"""Seven version-1 Interview Scenario fixtures (AIP-013 §6.2).

Stage weights sum to 100 per fixture. Budgets follow the global policy:
15:3/5, 30:5/3, 45:7/5, 60:9/7 (main_questions/followups); max follow-up
depth 2; skip allowance 1 for 15/30 and 2 for 45/60; difficulty
basic/standard/challenge; language zh-CN/en; mode text.
"""

from __future__ import annotations

from backend.domain.interview_scenario.enums import (
    CoverageCategory,
    DurationMinutes,
    ScenarioDifficulty,
    ScenarioLanguage,
    ScenarioStage,
)
from backend.domain.interview_scenario.schemas import (
    InterviewScenario,
    ScenarioDurationBudget,
    ScenarioScoring,
    ScenarioStageConfig,
)

_MAIN_EMPHASIS: dict[str, str] = {
    "comprehensive": "Balanced role simulation",
    "hr_screen": "Fit, motivation, communication",
    "technical_first": "Required skills and reasoning",
    "project_deep_dive": "Evidence and ownership",
    "system_design": "Design decisions and constraints",
    "behavioral": "STAR evidence and reflection",
    "manager_round": "Scope, judgment, growth",
}

_DIMENSIONS = ["technical", "engineering", "communication", "problem_solving", "behavioral"]
_PROMPT_POLICY = "plan-v1"

_DEFAULT_DIFFICULTIES = [
    ScenarioDifficulty.BASIC,
    ScenarioDifficulty.STANDARD,
    ScenarioDifficulty.CHALLENGE,
]
_DEFAULT_LANGUAGES = [ScenarioLanguage.ZH_CN, ScenarioLanguage.EN]


def _budgets() -> list[ScenarioDurationBudget]:
    return [
        ScenarioDurationBudget(
            duration=DurationMinutes.MINUTES_15,
            main_questions=3,
            total_followups=1,
            max_followup_depth=2,
            skip_allowance=1,
        ),
        ScenarioDurationBudget(
            duration=DurationMinutes.MINUTES_30,
            main_questions=5,
            total_followups=3,
            max_followup_depth=2,
            skip_allowance=1,
        ),
        ScenarioDurationBudget(
            duration=DurationMinutes.MINUTES_45,
            main_questions=7,
            total_followups=5,
            max_followup_depth=2,
            skip_allowance=2,
        ),
        ScenarioDurationBudget(
            duration=DurationMinutes.MINUTES_60,
            main_questions=9,
            total_followups=7,
            max_followup_depth=2,
            skip_allowance=2,
        ),
    ]


def _scoring() -> ScenarioScoring:
    return ScenarioScoring(dimensions=_DIMENSIONS, prompt_policy_version=_PROMPT_POLICY)


def _candidate_stage() -> ScenarioStageConfig:
    return ScenarioStageConfig(
        stage=ScenarioStage.CANDIDATE_QUESTIONS,
        weight=10,
        coverage_categories=[CoverageCategory.CANDIDATE_QUESTIONS],
        allows_candidate_questions=True,
    )


def _stage(stage: ScenarioStage, weight: int, coverage: list[CoverageCategory]) -> ScenarioStageConfig:
    return ScenarioStageConfig(stage=stage, weight=weight, coverage_categories=coverage)


def _fixture(
    key: str,
    stages: list[ScenarioStageConfig],
    coverage: list[CoverageCategory],
    *,
    candidate_min: int = 1,
    candidate_max: int = 3,
) -> InterviewScenario:
    total = sum(s.weight for s in stages)
    if total != 100:
        # Guard: caller must provide weights summing to 100; registry validation
        # will also re-check, but fail here deterministically.
        raise ValueError(f"fixture {key} stage weights sum to {total}, expected 100")
    return InterviewScenario(
        key=key,
        version=1,
        name_key=f"scenario.{key}.name",
        description_key=f"scenario.{key}.description",
        stages=stages,
        durations=_budgets(),
        allowed_coverage_categories=coverage,
        allowed_difficulties=_DEFAULT_DIFFICULTIES,
        allowed_languages=_DEFAULT_LANGUAGES,
        candidate_questions_min=candidate_min,
        candidate_questions_max=candidate_max,
        scoring=_scoring(),
    )


def build_fixtures() -> list[InterviewScenario]:
    """Return all seven version-1 fixtures. Fails on invalid fixture data."""
    comprehensive = _fixture(
        "comprehensive",
        [
            _stage(ScenarioStage.INTRODUCTION, 5, [CoverageCategory.COMMUNICATION]),
            _stage(ScenarioStage.CORE_SKILLS, 25, [CoverageCategory.CORE_SKILLS]),
            _stage(ScenarioStage.PROJECT, 25, [CoverageCategory.PROJECT_EVIDENCE]),
            _stage(ScenarioStage.SYSTEM_DESIGN, 15, [CoverageCategory.SYSTEM_DESIGN]),
            _stage(ScenarioStage.BEHAVIOR, 20, [CoverageCategory.BEHAVIORAL]),
            _candidate_stage(),
        ],
        [
            CoverageCategory.CORE_SKILLS,
            CoverageCategory.PROJECT_EVIDENCE,
            CoverageCategory.SYSTEM_DESIGN,
            CoverageCategory.BEHAVIORAL,
            CoverageCategory.COMMUNICATION,
            CoverageCategory.CANDIDATE_QUESTIONS,
        ],
    )

    hr_screen = _fixture(
        "hr_screen",
        [
            _stage(ScenarioStage.INTRODUCTION, 10, [CoverageCategory.COMMUNICATION]),
            _stage(ScenarioStage.BACKGROUND, 25, [CoverageCategory.TECHNICAL]),
            _stage(ScenarioStage.MOTIVATION, 25, [CoverageCategory.MOTIVATION]),
            _stage(ScenarioStage.BEHAVIOR, 30, [CoverageCategory.CULTURE_FIT]),
            _candidate_stage(),
        ],
        [
            CoverageCategory.MOTIVATION,
            CoverageCategory.CULTURE_FIT,
            CoverageCategory.COMMUNICATION,
            CoverageCategory.TECHNICAL,
            CoverageCategory.CANDIDATE_QUESTIONS,
        ],
    )

    technical_first = _fixture(
        "technical_first",
        [
            _stage(ScenarioStage.INTRODUCTION, 5, [CoverageCategory.COMMUNICATION]),
            _stage(ScenarioStage.CORE_SKILLS, 35, [CoverageCategory.CORE_SKILLS]),
            _stage(ScenarioStage.PROBLEM_SOLVING, 20, [CoverageCategory.PROBLEM_SOLVING]),
            _stage(ScenarioStage.PROJECT, 30, [CoverageCategory.PROJECT_EVIDENCE]),
            _candidate_stage(),
        ],
        [
            CoverageCategory.CORE_SKILLS,
            CoverageCategory.PROBLEM_SOLVING,
            CoverageCategory.PROJECT_EVIDENCE,
            CoverageCategory.COMMUNICATION,
            CoverageCategory.CANDIDATE_QUESTIONS,
        ],
    )

    project_deep_dive = _fixture(
        "project_deep_dive",
        [
            _stage(ScenarioStage.INTRODUCTION, 5, [CoverageCategory.COMMUNICATION]),
            _stage(ScenarioStage.PROJECT_CONTEXT, 15, [CoverageCategory.PROJECT_EVIDENCE]),
            _stage(ScenarioStage.PROJECT_DECISIONS, 25, [CoverageCategory.OWNERSHIP]),
            _stage(ScenarioStage.TRADEOFFS, 20, [CoverageCategory.PROBLEM_SOLVING]),
            _stage(ScenarioStage.OUTCOMES, 25, [CoverageCategory.PROJECT_EVIDENCE]),
            _candidate_stage(),
        ],
        [
            CoverageCategory.PROJECT_EVIDENCE,
            CoverageCategory.OWNERSHIP,
            CoverageCategory.PROBLEM_SOLVING,
            CoverageCategory.COMMUNICATION,
            CoverageCategory.CANDIDATE_QUESTIONS,
        ],
    )

    system_design = _fixture(
        "system_design",
        [
            _stage(ScenarioStage.CLARIFICATION, 10, [CoverageCategory.TECHNICAL]),
            _stage(ScenarioStage.ARCHITECTURE, 25, [CoverageCategory.SYSTEM_DESIGN]),
            _stage(ScenarioStage.DATA, 15, [CoverageCategory.SYSTEM_DESIGN]),
            _stage(ScenarioStage.SCALING, 20, [CoverageCategory.SYSTEM_DESIGN]),
            _stage(ScenarioStage.RELIABILITY, 10, [CoverageCategory.SYSTEM_DESIGN]),
            _stage(ScenarioStage.TRADEOFFS, 10, [CoverageCategory.PROBLEM_SOLVING]),
            _candidate_stage(),
        ],
        [
            CoverageCategory.SYSTEM_DESIGN,
            CoverageCategory.TECHNICAL,
            CoverageCategory.PROBLEM_SOLVING,
            CoverageCategory.CANDIDATE_QUESTIONS,
        ],
    )

    behavioral = _fixture(
        "behavioral",
        [
            _stage(ScenarioStage.INTRODUCTION, 5, [CoverageCategory.COMMUNICATION]),
            _stage(ScenarioStage.OWNERSHIP, 25, [CoverageCategory.OWNERSHIP]),
            _stage(ScenarioStage.COLLABORATION, 20, [CoverageCategory.CULTURE_FIT]),
            _stage(ScenarioStage.CONFLICT, 20, [CoverageCategory.BEHAVIORAL]),
            _stage(ScenarioStage.LEARNING, 20, [CoverageCategory.BEHAVIORAL]),
            _candidate_stage(),
        ],
        [
            CoverageCategory.BEHAVIORAL,
            CoverageCategory.CULTURE_FIT,
            CoverageCategory.OWNERSHIP,
            CoverageCategory.COMMUNICATION,
            CoverageCategory.CANDIDATE_QUESTIONS,
        ],
    )

    manager_round = _fixture(
        "manager_round",
        [
            _stage(ScenarioStage.INTRODUCTION, 5, [CoverageCategory.COMMUNICATION]),
            _stage(ScenarioStage.PRIORITIZATION, 25, [CoverageCategory.LEADERSHIP]),
            _stage(ScenarioStage.LEADERSHIP, 25, [CoverageCategory.LEADERSHIP]),
            _stage(ScenarioStage.CROSS_FUNCTIONAL, 20, [CoverageCategory.CULTURE_FIT]),
            _stage(ScenarioStage.GROWTH, 15, [CoverageCategory.LEADERSHIP]),
            _candidate_stage(),
        ],
        [
            CoverageCategory.LEADERSHIP,
            CoverageCategory.CULTURE_FIT,
            CoverageCategory.COMMUNICATION,
            CoverageCategory.CANDIDATE_QUESTIONS,
        ],
    )

    return [
        comprehensive,
        hr_screen,
        technical_first,
        project_deep_dive,
        system_design,
        behavioral,
        manager_round,
    ]


MAIN_EMPHASIS = _MAIN_EMPHASIS
