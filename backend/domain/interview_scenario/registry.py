"""Interview Scenario registry (AIP-013 §6.1, §6.3).

In-process, read-only, code-backed. Construction validates every fixture and
fails deterministically on duplicate/invalid data rather than falling back.
"""

from __future__ import annotations

from collections.abc import Iterator

from backend.domain.interview_scenario.enums import (
    ScenarioKey,
    ScenarioStage,
)
from backend.domain.interview_scenario.fixtures import MAIN_EMPHASIS, build_fixtures
from backend.domain.interview_scenario.schemas import (
    InterviewScenario,
    InterviewScenarioSummary,
)


class ScenarioRegistryError(Exception):
    """Base registry error."""


class ScenarioNotFoundError(ScenarioRegistryError):
    """Requested scenario key does not exist."""


class ScenarioVersionNotFoundError(ScenarioRegistryError):
    """Requested scenario version does not exist for the key."""


class ScenarioRegistryInvalidError(ScenarioRegistryError):
    """Registry fixture data is invalid; startup/tests must fail closed."""


_ALLOWED_DURATIONS = {15, 30, 45, 60}
_ALLOWED_SKIP = {15: 1, 30: 1, 45: 2, 60: 2}


def _validate_fixture(scenario: InterviewScenario) -> None:
    if sum(s.weight for s in scenario.stages) != 100:
        raise ScenarioRegistryInvalidError(
            f"scenario {scenario.key} stage weights sum to {sum(s.weight for s in scenario.stages)}, expected 100"
        )
    seen_stages: set[ScenarioStage] = set()
    for stage in scenario.stages:
        if stage.stage in seen_stages:
            raise ScenarioRegistryInvalidError(f"scenario {scenario.key} duplicate stage {stage.stage}")
        seen_stages.add(stage.stage)
    for budget in scenario.durations:
        if budget.duration.value not in _ALLOWED_DURATIONS:
            raise ScenarioRegistryInvalidError(
                f"scenario {scenario.key} invalid duration {budget.duration.value}"
            )
        allowed_skip = _ALLOWED_SKIP[budget.duration.value]
        if budget.skip_allowance > allowed_skip:
            raise ScenarioRegistryInvalidError(
                f"scenario {scenario.key} duration {budget.duration.value} "
                f"skip allowance {budget.skip_allowance} exceeds global {allowed_skip}"
            )
    if not scenario.allowed_difficulties:
        raise ScenarioRegistryInvalidError(f"scenario {scenario.key} has no allowed difficulties")
    if not scenario.allowed_languages:
        raise ScenarioRegistryInvalidError(f"scenario {scenario.key} has no allowed languages")
    if scenario.candidate_questions_max > 3:
        raise ScenarioRegistryInvalidError(
            f"scenario {scenario.key} candidate_questions_max > 3"
        )
    if scenario.mode != "text":
        raise ScenarioRegistryInvalidError(f"scenario {scenario.key} mode must be text")
    # Ensure every stage coverage category is within the scenario allow-list.
    allowed = set(scenario.allowed_coverage_categories)
    for stage in scenario.stages:
        for cat in stage.coverage_categories:
            if cat not in allowed:
                raise ScenarioRegistryInvalidError(
                    f"scenario {scenario.key} stage {stage.stage} coverage {cat} not in allow-list"
                )


class ScenarioRegistry:
    """Validated read-only registry of versioned scenarios."""

    def __init__(self, fixtures: list[InterviewScenario] | None = None) -> None:
        raw = fixtures if fixtures is not None else build_fixtures()
        self._by_key: dict[str, dict[int, InterviewScenario]] = {}
        for scenario in raw:
            _validate_fixture(scenario)
            by_version = self._by_key.setdefault(scenario.key, {})
            if scenario.version in by_version:
                raise ScenarioRegistryInvalidError(
                    f"duplicate scenario {scenario.key} version {scenario.version}"
                )
            by_version[scenario.version] = scenario
        self._active: dict[str, InterviewScenario] = {
            key: versions[max(versions)] for key, versions in self._by_key.items()
        }

    def keys(self) -> list[str]:
        return list(self._by_key.keys())

    def list_active(self) -> tuple[InterviewScenarioSummary, ...]:
        return tuple(
            InterviewScenarioSummary(
                key=s.key,
                version=s.version,
                name_key=s.name_key,
                description_key=s.description_key,
                stage_keys=[str(st.stage.value) for st in s.stages],
                main_emphasis=MAIN_EMPHASIS.get(s.key, ""),
            )
            for s in self._active.values()
        )

    def get(self, key: str, version: int | None = None) -> InterviewScenario:
        by_version = self._by_key.get(key)
        if by_version is None:
            raise ScenarioNotFoundError(f"scenario {key} not found")
        if version is None:
            return self._active[key]
        scenario = by_version.get(version)
        if scenario is None:
            raise ScenarioVersionNotFoundError(
                f"scenario {key} version {version} not found"
            )
        return scenario

    def __iter__(self) -> Iterator[InterviewScenario]:
        return iter(self._active.values())


_registry: ScenarioRegistry | None = None


def get_registry() -> ScenarioRegistry:
    """Return the process-wide validated registry singleton."""
    global _registry
    if _registry is None:
        _registry = ScenarioRegistry()
    return _registry


def scenario_keys() -> list[str]:
    return [k.value for k in ScenarioKey]
