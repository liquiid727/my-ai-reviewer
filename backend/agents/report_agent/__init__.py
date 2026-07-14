"""面试报告生成 Agent —— 综合所有问答记录生成结构化面试报告。"""

import json
import logging

from pydantic import ValidationError

from backend.domain.interview.schemas import InterviewReport
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.report_gen import (
    REPORT_GEN_SYSTEM_PROMPT,
    REPORT_GEN_USER_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 1


class ReportGenerationAgent:
    """调用 LLM 综合所有面试数据生成面试报告。"""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.model_info: str = ""

    async def generate(self, interview_data: dict) -> InterviewReport:
        messages = [
            {"role": "system", "content": REPORT_GEN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": REPORT_GEN_USER_PROMPT.format(
                    interview_data=json.dumps(interview_data, ensure_ascii=False, default=str),
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
                return InterviewReport(**data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning("Report generation attempt %d failed: %s", attempt + 1, str(exc)[:200])
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Validation error: {exc}. Fix the JSON and return ONLY valid JSON.",
                        }
                    )

        raise ValueError(f"Report generation failed after {MAX_RETRIES + 1} attempts: {last_error}")
