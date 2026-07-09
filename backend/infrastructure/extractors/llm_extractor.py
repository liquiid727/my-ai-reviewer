"""LLM 简历信息提取器 —— 调用大模型从原始文本中提取结构化信息。"""

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

# 输入文本最大长度（超出部分截断）
MAX_TEXT_LENGTH = 30_000
# JSON 解析失败时的最大重试次数
MAX_RETRIES = 1


class LLMResumeExtractor(ResumeExtractor):
    """基于 LLM 的简历信息提取器。

    将简历原始文本发送给大模型，提取候选人画像、事实列表等结构化数据。
    如果 LLM 返回的 JSON 格式不正确，会自动重试（带上错误信息提示模型修正）。
    """
    version: str = "llm-extractor-v1"

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.token_usage: dict = {}   # 本次调用的 token 用量
        self.model_info: str = ""     # 使用的模型名称

    async def extract(self, raw_text: str) -> dict:
        """从原始文本中提取结构化信息。"""
        # 截断过长的文本，防止超出模型上下文窗口
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
                # 重试时将上次的响应和错误信息加入对话，帮助模型自我修正
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
    """解析 JSON 并用 Pydantic 模型校验数据结构。"""
    data = json.loads(content)

    # 校验候选人画像结构
    if "profile" in data:
        CandidateProfile(**data["profile"])

    # 校验每条事实的结构
    if "facts" in data:
        for fact_data in data["facts"]:
            ResumeFact(**fact_data)

    return data
