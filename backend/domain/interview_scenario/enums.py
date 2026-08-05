"""Interview Scenario domain value objects (AIP-013).

Scenario definitions are code-backed fixtures. They carry public policy only:
stage names/weights, coverage categories, budgets, skip allowance, difficulty,
language, and scoring dimensions. They never carry prompts, planned questions,
expected signals, or scoring rubrics.
"""

from __future__ import annotations

from enum import Enum


class ScenarioKey(str, Enum):
    """The seven first-release interview scenarios."""

    COMPREHENSIVE = "comprehensive"
    HR_SCREEN = "hr_screen"
    TECHNICAL_FIRST = "technical_first"
    PROJECT_DEEP_DIVE = "project_deep_dive"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    MANAGER_ROUND = "manager_round"


class ScenarioStage(str, Enum):
    """Stable stage identifiers usable across all seven scenarios."""

    INTRODUCTION = "introduction"
    BACKGROUND = "background"
    MOTIVATION = "motivation"
    CORE_SKILLS = "core_skills"
    PROBLEM_SOLVING = "problem_solving"
    PROJECT = "project"
    PROJECT_CONTEXT = "project_context"
    PROJECT_DECISIONS = "project_decisions"
    TRADEOFFS = "tradeoffs"
    OUTCOMES = "outcomes"
    SYSTEM_DESIGN = "system_design"
    CLARIFICATION = "clarification"
    ARCHITECTURE = "architecture"
    DATA = "data"
    SCALING = "scaling"
    RELIABILITY = "reliability"
    BEHAVIOR = "behavior"
    OWNERSHIP = "ownership"
    COLLABORATION = "collaboration"
    CONFLICT = "conflict"
    LEARNING = "learning"
    PRIORITIZATION = "prioritization"
    LEADERSHIP = "leadership"
    CROSS_FUNCTIONAL = "cross_functional"
    GROWTH = "growth"
    CANDIDATE_QUESTIONS = "candidate_questions"


class CoverageCategory(str, Enum):
    """Allowed coverage categories referenced by scenario fixtures."""

    CORE_SKILLS = "core_skills"
    PROBLEM_SOLVING = "problem_solving"
    PROJECT_EVIDENCE = "project_evidence"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    MOTIVATION = "motivation"
    CULTURE_FIT = "culture_fit"
    LEADERSHIP = "leadership"
    OWNERSHIP = "ownership"
    TECHNICAL = "technical"
    COMMUNICATION = "communication"
    CANDIDATE_QUESTIONS = "candidate_questions"


class DurationMinutes(int, Enum):
    MINUTES_15 = 15
    MINUTES_30 = 30
    MINUTES_45 = 45
    MINUTES_60 = 60


class ScenarioDifficulty(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    CHALLENGE = "challenge"


class ScenarioLanguage(str, Enum):
    ZH_CN = "zh-CN"
    EN = "en"
