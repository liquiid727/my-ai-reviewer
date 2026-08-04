"""LLM 简历要点润色器 —— 调用大模型在不编造事实的前提下重写要点。"""

from __future__ import annotations

import json
import logging

from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.schemas import PolishResult
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.polish import (
    RESUME_POLISH_SYSTEM_PROMPT,
    RESUME_POLISH_USER_PROMPT,
)
from backend.infrastructure.polishers.base import ResumePolisher

logger = logging.getLogger(__name__)

# JSON 解析失败时的最大重试次数
MAX_RETRIES = 1


class LLMResumePolisher(ResumePolisher):
    """基于 LLM 的简历要点润色器。

    将一组要点发送给大模型，返回润色后的建议（保留原文，供前端逐条 diff 接受）。
    如果模型返回的 JSON 不合法或条目数量不匹配，会自动重试一次。
    """
    version: str = "llm-polisher-v1"

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def polish(
        self,
        section_type: ResumeSectionType,
        items: list[str],
        context: str | None = None,
    ) -> PolishResult:
        """润色一组要点，返回原文与建议。空输入直接返回空结果。"""
        cleaned = [item for item in items if item and item.strip()]
        if not cleaned:
            return PolishResult(original_items=[], polished_items=[], notes=None)

        context_line = f"Target role / context: {context}\n" if context else ""
        numbered = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(cleaned))
        user_prompt = RESUME_POLISH_USER_PROMPT.format(
            section_type=section_type.value,
            context_line=context_line,
            count=len(cleaned),
            items=numbered,
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": RESUME_POLISH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            response = await self._gateway.complete(
                messages=messages,
                response_format={"type": "json_object"},
                privacy_required=True,
            )

            try:
                polished, notes = _parse_polish(response.content, expected_count=len(cleaned))
                return PolishResult(
                    original_items=cleaned,
                    polished_items=polished,
                    notes=notes,
                )
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.warning("Polish attempt %d failed: %s", attempt + 1, str(exc)[:200])
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Your previous response was invalid: {exc}. "
                            f"Return ONLY valid JSON with a 'polished_items' array of exactly "
                            f"{len(cleaned)} strings in the same order."
                        ),
                    })

        raise ValueError(f"Failed to polish after {MAX_RETRIES + 1} attempts: {last_error}")


def _parse_polish(content: str, expected_count: int) -> tuple[list[str], str | None]:
    """解析 LLM 返回的润色结果（兼容 markdown 代码块包裹）。"""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Response is not a JSON object")

    polished = data.get("polished_items")
    if not isinstance(polished, list):
        raise ValueError("'polished_items' must be a list")
    if len(polished) != expected_count:
        raise ValueError(
            f"'polished_items' has {len(polished)} items, expected {expected_count}"
        )
    if not all(isinstance(item, str) for item in polished):
        raise ValueError("'polished_items' must contain only strings")

    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        notes = None

    return polished, notes
