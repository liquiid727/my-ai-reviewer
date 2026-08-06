"""Structured LLM matcher for evidence-bound JD matching."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.domain.jd.matching_v2 import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    DimensionStatus,
    SourceCatalogEntry,
    validate_dimension_evidence,
)
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base import LLMResponse


class LLMJDMatcherError(ValueError):
    """Safe matcher failure."""


class LLMDimensionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensions: list[DimensionScore] = Field(min_length=1, max_length=7)


class EvidenceBoundJDMatcher:
    """Call the configured LLM with minimized catalog evidence and validate references."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.last_usage: dict[str, Any] = {}
        self.last_model: str | None = None

    async def score_dimensions(
        self,
        *,
        jd_summary: dict[str, Any],
        catalog: list[SourceCatalogEntry],
    ) -> list[DimensionScore]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You score job-description fit using only the provided evidence catalog. "
                    "Return JSON with dimensions only. Use null score and status unknown "
                    "when evidence is insufficient. Never cite an evidence id that is not present."
                ),
            },
            {
                "role": "user",
                "content": (
                    "JD summary:\n"
                    f"{_safe_json(jd_summary)}\n\n"
                    "Dimension weights:\n"
                    f"{_safe_json(DIMENSION_WEIGHTS)}\n\n"
                    "Evidence catalog:\n"
                    f"{_safe_json([entry.model_dump() for entry in catalog])}"
                ),
            },
        ]
        schema = LLMDimensionOutput.model_json_schema()
        try:
            response = await self._gateway.complete(
                messages, response_format={"type": "json_object", "schema": schema}, privacy_required=True
            )
            output = _parse_response(response)
        except ValidationError as exc:
            raise LLMJDMatcherError("JD matcher returned invalid structured output") from exc
        except Exception as exc:
            raise LLMJDMatcherError("JD matcher failed") from exc
        validate_dimension_evidence(output.dimensions, catalog)
        normalized = _complete_dimensions(output.dimensions)
        self.last_usage = response.usage
        self.last_model = response.model
        return normalized


class HeuristicJDMatcher:
    """Deterministic fallback used by tests and when no live LLM is injected."""

    last_usage: dict[str, Any] = {}
    last_model: str | None = "heuristic-v2"

    async def score_dimensions(
        self,
        *,
        jd_summary: dict[str, Any],
        catalog: list[SourceCatalogEntry],
    ) -> list[DimensionScore]:
        jd_ids = [entry.id for entry in catalog if entry.source == "jd"][:3]
        candidate_ids = [entry.id for entry in catalog if entry.source != "jd"][:3]
        has_candidate = bool(candidate_ids)
        dimensions: list[DimensionScore] = []
        for name, weight in DIMENSION_WEIGHTS.items():
            dimensions.append(
                DimensionScore(
                    dimension=name,
                    weight=weight,
                    score=72.0 if has_candidate else None,
                    status=DimensionStatus.PARTIAL if has_candidate else DimensionStatus.UNKNOWN,
                    reason="Synthetic evidence supports a partial fit."
                    if has_candidate
                    else "Insufficient candidate evidence.",
                    jd_evidence_ids=jd_ids[:1],
                    candidate_evidence_ids=candidate_ids[:1],
                    confidence=0.68 if has_candidate else 0.2,
                )
            )
        return dimensions


def _safe_json(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _parse_response(response: LLMResponse) -> LLMDimensionOutput:
    import json

    payload = json.loads(response.content)
    return LLMDimensionOutput.model_validate(payload)


def _complete_dimensions(dimensions: list[DimensionScore]) -> list[DimensionScore]:
    by_name = {dimension.dimension: dimension for dimension in dimensions}
    complete: list[DimensionScore] = []
    for name, weight in DIMENSION_WEIGHTS.items():
        existing = by_name.get(name)
        if existing is None:
            complete.append(
                DimensionScore(
                    dimension=name,
                    weight=weight,
                    score=None,
                    status=DimensionStatus.UNKNOWN,
                    reason="Dimension was not supported by the model output.",
                    confidence=0.0,
                )
            )
        elif existing.weight != weight:
            complete.append(existing.model_copy(update={"weight": weight}))
        else:
            complete.append(existing)
    return complete


__all__ = ["EvidenceBoundJDMatcher", "HeuristicJDMatcher", "LLMJDMatcherError"]
