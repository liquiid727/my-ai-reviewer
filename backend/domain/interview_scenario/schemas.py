"""Interview Scenario Pydantic value objects (AIP-013)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.domain.interview_scenario.enums import (
    CoverageCategory,
    DurationMinutes,
    ScenarioDifficulty,
    ScenarioLanguage,
    ScenarioStage,
)


class ScenarioStageWeight(BaseModel):
    """One ordered stage with an integer weight contributing to the 100 total."""

    stage: ScenarioStage
    weight: int = Field(ge=0, le=100)


class ScenarioStageConfig(BaseModel):
    """Per-stage coverage and candidate-question allowance."""

    stage: ScenarioStage
    weight: int = Field(ge=0, le=100)
    coverage_categories: list[CoverageCategory] = Field(default_factory=list)
    # Candidate-question allowance applies only to the candidate_questions stage.
    allows_candidate_questions: bool = False


class ScenarioDurationBudget(BaseModel):
    """Main-question and total follow-up budgets for one duration."""

    duration: DurationMinutes
    main_questions: int = Field(ge=1, le=9)
    total_followups: int = Field(ge=0, le=7)
    max_followup_depth: int = Field(default=2, ge=1, le=2)
    skip_allowance: int = Field(default=1, ge=0, le=2)


class ScenarioScoring(BaseModel):
    """Public scoring dimensions and the prompt-policy version."""

    dimensions: list[str] = Field(min_length=1)
    prompt_policy_version: str


class InterviewScenario(BaseModel):
    """A versioned code-backed scenario with public policy only."""

    key: str
    version: int = Field(ge=1)
    name_key: str
    description_key: str
    stages: list[ScenarioStageConfig]
    durations: list[ScenarioDurationBudget]
    allowed_coverage_categories: list[CoverageCategory] = Field(default_factory=list)
    allowed_difficulties: list[ScenarioDifficulty] = Field(default_factory=list)
    allowed_languages: list[ScenarioLanguage] = Field(default_factory=list)
    candidate_questions_min: int = Field(default=0, ge=0, le=3)
    candidate_questions_max: int = Field(default=0, ge=0, le=3)
    scoring: ScenarioScoring
    mode: Literal["text"] = "text"

    @model_validator(mode="after")
    def _validate_scenario(self) -> "InterviewScenario":
        if sum(s.weight for s in self.stages) != 100:
            raise ValueError(f"scenario {self.key} stage weights must sum to 100")
        stage_keys = [s.stage for s in self.stages]
        if len(stage_keys) != len(set(stage_keys)):
            raise ValueError(f"scenario {self.key} has duplicate stages")
        if self.candidate_questions_max < self.candidate_questions_min:
            raise ValueError("candidate_questions_max must be >= candidate_questions_min")
        if self.candidate_questions_max > 3:
            raise ValueError("candidate_questions_max must be <= 3")
        return self


class InterviewScenarioSummary(BaseModel):
    """Lightweight list-item view."""

    key: str
    version: int
    name_key: str
    description_key: str
    stage_keys: list[str]
    main_emphasis: str
