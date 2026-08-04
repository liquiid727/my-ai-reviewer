"""通过 LLM 生成受限的简历修改提案。"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.domain.resume_builder.editing import (
    EditOperation,
    EditProposalResult,
    materialize_operations,
)
from backend.domain.resume_builder.schemas import ResumeDraft
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.resume_edit import (
    RESUME_EDIT_SYSTEM_PROMPT,
    RESUME_EDIT_USER_PROMPT,
)

logger = logging.getLogger(__name__)
MAX_RETRIES = 1


class _ModelProposal(BaseModel):
    assistant_message: str = Field(min_length=1, max_length=4000)
    operations: list[EditOperation] = Field(default_factory=list, max_length=30)


class LLMResumeEditor:
    """外部 LLM 适配器；只返回经领域契约校验的提案。"""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def propose(self, draft: ResumeDraft, instruction: str) -> EditProposalResult:
        draft_json = json.dumps(draft.model_dump(mode="json"), ensure_ascii=False)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": RESUME_EDIT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": RESUME_EDIT_USER_PROMPT.format(
                    instruction=instruction,
                    draft_json=draft_json,
                ),
            },
        ]
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            response = await self._gateway.complete(
                messages=messages,
                response_format={"type": "json_object"},
                privacy_required=True,
            )
            try:
                parsed = _parse_response(response.content)
                operations = materialize_operations(draft, parsed.operations)
                return EditProposalResult(
                    assistant_message=parsed.assistant_message,
                    operations=operations,
                    model=response.model,
                    usage=dict(response.usage),
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                logger.warning("Resume edit proposal attempt %d failed: %s", attempt + 1, str(exc)[:200])
                if attempt < MAX_RETRIES:
                    messages.extend([
                        {"role": "assistant", "content": response.content},
                        {
                            "role": "user",
                            "content": f"The response was invalid: {exc}. Return only a valid proposal JSON object.",
                        },
                    ])

        raise ValueError(f"Failed to produce a valid edit proposal: {last_error}")


def _parse_response(content: str) -> _ModelProposal:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return _ModelProposal.model_validate(json.loads(text))
