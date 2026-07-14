"""面试出题 Agent —— 根据简历和 JD 生成面试题目。"""

import json
import logging

from pydantic import ValidationError

from backend.domain.interview.schemas import QuestionGenerationOutput
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.question_gen import (
    QUESTION_GEN_SYSTEM_PROMPT,
    QUESTION_GEN_USER_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 1


class QuestionGenerationAgent:
    """调用 LLM 根据简历画像和 JD 生成面试题目。"""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.model_info: str = ""

    async def generate(
        self,
        resume_data: dict,
        jd_text: str,
        count: int,
        experience_level: str = "Mid",
    ) -> QuestionGenerationOutput:
        jd_display = jd_text if jd_text else "No JD provided. Generate all questions based on the resume."

        messages = [
            {"role": "system", "content": QUESTION_GEN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": QUESTION_GEN_USER_PROMPT.format(
                    count=count,
                    jd_text=jd_display,
                    resume_data=json.dumps(resume_data, ensure_ascii=False, default=str),
                    experience_level=experience_level,
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
                return QuestionGenerationOutput(**data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning("Question generation attempt %d failed: %s", attempt + 1, str(exc)[:200])
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Validation error: {exc}. Fix the JSON and return ONLY valid JSON.",
                        }
                    )

        raise ValueError(f"Question generation failed after {MAX_RETRIES + 1} attempts: {last_error}")
