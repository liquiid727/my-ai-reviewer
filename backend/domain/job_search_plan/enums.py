"""Lifecycle values for generated job-search plans."""

from enum import StrEnum


class PlanStatus(StrEnum):
    GENERATING = "generating"
    REGENERATING = "regenerating"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanTaskCategory(StrEnum):
    GAP_PRIORITY = "gap_priority"
    RESUME = "resume"
    SKILL = "skill"
    EVIDENCE_PROJECT = "evidence_project"
    INTERVIEW = "interview"
    APPLICATION_REVIEW = "application_review"


class PlanTaskSource(StrEnum):
    AI = "ai"
    MANUAL = "manual"


class PlanTaskPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlanTaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


PLAN_TASK_CATEGORIES = tuple(category.value for category in PlanTaskCategory)
