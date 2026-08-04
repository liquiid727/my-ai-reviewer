"""Strict LLM adapter for evidence-bound plan task generation."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from backend.domain.job_search_plan.enums import PLAN_TASK_CATEGORIES
from backend.domain.job_search_plan.schemas import CatalogEntry, PlanGenerationOutput
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.plan_generation import (
    PLAN_GENERATION_SYSTEM_PROMPT,
    PLAN_GENERATION_USER_PROMPT,
)


class LLMPlanGenerationError(ValueError):
    """The provider response cannot safely become persistent plan tasks."""


class LLMPlanGenerator:
    """Generate and validate a complete plan against a fixed source catalog."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.model_info = ""
        self.token_usage: dict[str, Any] = {}

    async def generate(
        self,
        catalog: list[CatalogEntry],
        *,
        target_date: str,
        weekly_hours: int,
    ) -> PlanGenerationOutput:
        messages = [
            {"role": "system", "content": PLAN_GENERATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": PLAN_GENERATION_USER_PROMPT.format(
                    target_date=target_date,
                    weekly_hours=weekly_hours,
                    catalog_json=json.dumps([entry.model_dump() for entry in catalog], ensure_ascii=False),
                ),
            },
        ]
        try:
            response = await self._gateway.complete(messages=messages, response_format={"type": "json_object"})
        except Exception as exc:
            raise LLMPlanGenerationError("Plan generation request failed") from exc
        self.model_info = response.model
        self.token_usage = response.usage
        try:
            output = PlanGenerationOutput.model_validate(json.loads(response.content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMPlanGenerationError("Plan generation returned an invalid structure") from exc
        self._validate_output(output, catalog)
        return output

    @staticmethod
    def _validate_output(output: PlanGenerationOutput, catalog: list[CatalogEntry]) -> None:
        known_basis_ids = {entry.id for entry in catalog}
        if len(known_basis_ids) != len(catalog):
            raise LLMPlanGenerationError("Source catalog contains duplicate IDs")
        categories = {task.category.value for task in output.tasks}
        if categories != set(PLAN_TASK_CATEGORIES):
            raise LLMPlanGenerationError("Plan must include every task category")
        titles = [task.title.strip().casefold() for task in output.tasks]
        if any(not title for title in titles):
            raise LLMPlanGenerationError("Plan task titles cannot be empty")
        if len(set(titles)) != len(titles):
            raise LLMPlanGenerationError("Plan task titles must be unique")
        if any(not task.description.strip() for task in output.tasks):
            raise LLMPlanGenerationError("Plan task descriptions cannot be empty")
        unknown = {basis_id for task in output.tasks for basis_id in task.basis_ids} - known_basis_ids
        if unknown:
            raise LLMPlanGenerationError("Plan referenced unknown source evidence")
