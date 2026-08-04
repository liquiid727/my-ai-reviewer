"""Strict request and worker contracts for job-search plans."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.domain.job_search_plan.enums import (
    PlanStatus,
    PlanTaskCategory,
    PlanTaskPriority,
    PlanTaskSource,
    PlanTaskStatus,
)


class PlanContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanCreateRequest(PlanContract):
    jd_id: uuid.UUID
    resume_id: uuid.UUID
    title: str | None = Field(default=None, max_length=200)
    target_date: date | None = None
    weekly_hours: int | None = Field(default=None, ge=1, le=80)
    supplemental_background: str | None = Field(default=None, max_length=10_000)


class PlanPatchRequest(PlanContract):
    expected_revision: int = Field(ge=0)
    title: str | None = Field(default=None, max_length=200)
    target_date: date | None = None
    weekly_hours: int | None = Field(default=None, ge=1, le=80)
    supplemental_background: str | None = Field(default=None, max_length=10_000)


class PlanTaskCreateRequest(PlanContract):
    expected_revision: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=300)
    category: PlanTaskCategory
    description: str = Field(default="", max_length=3000)
    priority: PlanTaskPriority = PlanTaskPriority.MEDIUM
    status: PlanTaskStatus = PlanTaskStatus.TODO
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Task title cannot be empty")
        return value.strip()


class PlanTaskPatchRequest(PlanContract):
    expected_revision: int = Field(ge=0)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    category: PlanTaskCategory | None = None
    description: str | None = Field(default=None, max_length=3000)
    priority: PlanTaskPriority | None = None
    status: PlanTaskStatus | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def patched_title_must_contain_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Task title cannot be empty")
        return value.strip() if value is not None else None


class PlanTaskOrderRequest(PlanContract):
    expected_revision: int = Field(ge=0)
    task_ids: list[uuid.UUID] = Field(max_length=200)


class PlanRetryRequest(PlanContract):
    expected_revision: int = Field(ge=0)


class PlanRegenerateRequest(PlanContract):
    expected_revision: int = Field(ge=0)


class CatalogEntry(PlanContract):
    id: str = Field(min_length=1, max_length=100)
    source: Literal["jd", "profile", "match", "preference"]
    label: str = Field(min_length=1, max_length=300)
    excerpt: str = Field(min_length=1, max_length=500)


class GeneratedPlanTask(PlanContract):
    title: str = Field(min_length=1, max_length=300)
    category: PlanTaskCategory
    description: str = Field(min_length=1, max_length=3000)
    priority: PlanTaskPriority
    due_offset_days: int = Field(ge=0, le=365)
    basis_ids: list[str] = Field(min_length=1, max_length=10)

    @field_validator("title", "description")
    @classmethod
    def generated_text_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Generated task text cannot be empty")
        return value.strip()


class PlanGenerationOutput(PlanContract):
    suggested_title: str = Field(min_length=1, max_length=200)
    tasks: list[GeneratedPlanTask] = Field(min_length=6, max_length=30)

    @field_validator("suggested_title")
    @classmethod
    def suggested_title_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Suggested title cannot be empty")
        return value.strip()


class PlanProgress(PlanContract):
    done: int = Field(ge=0)
    total: int = Field(ge=0)
    percent: int = Field(ge=0, le=100)


class PlanTaskData(PlanContract):
    id: uuid.UUID
    plan_id: uuid.UUID
    title: str
    category: PlanTaskCategory
    description: str
    basis: list[dict[str, str]] = Field(default_factory=list)
    source: PlanTaskSource
    priority: PlanTaskPriority
    status: PlanTaskStatus
    due_date: date | None
    sort_order: int


class PlanSummary(PlanContract):
    id: uuid.UUID
    title: str
    status: PlanStatus
    revision: int = Field(ge=0)
