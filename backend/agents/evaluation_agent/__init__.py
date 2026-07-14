"""回答评估 Agent —— 对候选人回答进行评分并判断是否需要追问。"""

import json
import logging

from pydantic import ValidationError

from backend.domain.interview.schemas import AnswerEvaluation
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.answer_eval import (
    ANSWER_EVAL_SYSTEM_PROMPT,
    ANSWER_EVAL_USER_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 1


class AnswerEvaluationAgent:
    """调用 LLM 评估候选人的回答质量，返回评分和追问判断。"""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.model_info: str = ""

    async def evaluate(
        self,
        question_text: str,
        expected_points: list[str],
        answer_text: str,
        followup_round: int = 0,
        previous_answers: list[dict] | None = None,
    ) -> AnswerEvaluation:
        previous_context = ""
        if previous_answers:
            parts = []
            for prev in previous_answers:
                parts.append(
                    f"## Previous Answer (round {prev.get('followup_round', 0)})\n"
                    f"Answer: {prev.get('answer_text', '')}\n"
                    f"Score: {prev.get('score', 'N/A')}, Feedback: {prev.get('feedback', 'N/A')}"
                )
            previous_context = "## Previous Rounds\n" + "\n\n".join(parts)

        messages = [
            {"role": "system", "content": ANSWER_EVAL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": ANSWER_EVAL_USER_PROMPT.format(
                    question_text=question_text,
                    expected_points=json.dumps(expected_points, ensure_ascii=False),
                    answer_text=answer_text,
                    followup_round=followup_round,
                    previous_context=previous_context,
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
                return AnswerEvaluation(**data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning("Answer evaluation attempt %d failed: %s", attempt + 1, str(exc)[:200])
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Validation error: {exc}. Fix the JSON and return ONLY valid JSON.",
                        }
                    )

        raise ValueError(f"Answer evaluation failed after {MAX_RETRIES + 1} attempts: {last_error}")
