"""追问生成 Agent —— 根据原题和候选人回答动态生成追问题目。"""

import json
import logging

from pydantic import ValidationError

from backend.domain.interview.schemas import FollowupOutput
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.followup_gen import (
    FOLLOWUP_GEN_SYSTEM_PROMPT,
    FOLLOWUP_GEN_USER_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 1


class FollowupGenerationAgent:
    """调用 LLM 根据候选人回答生成追问题目。"""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.model_info: str = ""

    async def generate(
        self,
        question_text: str,
        answer_text: str,
        score: float,
        feedback: str,
        key_points_missed: list[str],
        followup_reason: str | None = None,
    ) -> FollowupOutput:
        messages = [
            {"role": "system", "content": FOLLOWUP_GEN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": FOLLOWUP_GEN_USER_PROMPT.format(
                    question_text=question_text,
                    answer_text=answer_text,
                    score=score,
                    feedback=feedback,
                    key_points_missed=json.dumps(key_points_missed, ensure_ascii=False),
                    followup_reason=followup_reason or "N/A",
                ),
            },
        ]

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            response = await self._gateway.complete(
                messages=messages,
                response_format={"type": "json_object"},
            )
            self.model_info = response.model

            try:
                data = json.loads(response.content)
                return FollowupOutput(**data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning("Followup generation attempt %d failed: %s", attempt + 1, str(exc)[:200])
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Validation error: {exc}. Fix the JSON and return ONLY valid JSON.",
                        }
                    )

        raise ValueError(f"Followup generation failed after {MAX_RETRIES + 1} attempts: {last_error}")
