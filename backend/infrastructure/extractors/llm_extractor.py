import json
import logging

from pydantic import ValidationError

from backend.domain.resume.schemas import CandidateProfile, ResumeFact
from backend.infrastructure.extractors.base import ResumeExtractor
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.extraction import (
    RESUME_EXTRACTION_SYSTEM_PROMPT,
    RESUME_EXTRACTION_USER_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 30_000
MAX_RETRIES = 1


class LLMResumeExtractor(ResumeExtractor):
    version: str = "llm-extractor-v1"

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.token_usage: dict = {}
        self.model_info: str = ""

    async def extract(self, raw_text: str) -> dict:
        if len(raw_text) > MAX_TEXT_LENGTH:
            raw_text = raw_text[:MAX_TEXT_LENGTH]

        messages = [
            {"role": "system", "content": RESUME_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": RESUME_EXTRACTION_USER_PROMPT.format(resume_text=raw_text)},
        ]

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            response = await self._gateway.complete(
                messages=messages,
                response_format={"type": "json_object"},
            )

            self.token_usage = response.usage
            self.model_info = response.model

            try:
                parsed = _parse_and_validate(response.content)
                return parsed
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Extraction attempt %d failed: %s",
                    attempt + 1,
                    str(exc)[:200],
                )
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Your previous response had a validation error: {exc}. "
                            "Please fix the JSON and try again. Return ONLY valid JSON."
                        ),
                    })

        raise ValueError(f"Failed to extract valid data after {MAX_RETRIES + 1} attempts: {last_error}")


def _parse_and_validate(content: str) -> dict:
    data = json.loads(content)

    if "profile" in data:
        CandidateProfile(**data["profile"])

    if "facts" in data:
        for fact_data in data["facts"]:
            ResumeFact(**fact_data)

    return data
