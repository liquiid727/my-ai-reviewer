"""LLM JD 抽取器 —— 调用大模型从 JD 原文抽取 required_skills / responsibilities / seniority。

与 llm_extractor.py（简历抽取）同模式：复用 LLMGateway，结构化输出 + Pydantic 校验，
输出不合法时内部重试 1 次（带错误信息提示模型自我修正），仍失败抛 JDExtractionError。
"""

import json
import logging
from typing import Any

from pydantic import ValidationError

from backend.domain.jd.schemas import JDExtraction
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.jd_extraction import (
    JD_EXTRACTION_SYSTEM_PROMPT,
    JD_EXTRACTION_USER_PROMPT,
)

logger = logging.getLogger(__name__)

# 输入文本最大长度。导入服务会拒绝更大的正文，不静默截断。
MAX_TEXT_LENGTH = 100_000
# JSON 解析 / schema 校验失败时的最大重试次数
MAX_RETRIES = 1


class JDExtractionError(Exception):
    """JD 抽取失败（LLM 输出经重试后仍不合法）。"""


class JDExtractor:
    """基于 LLM 的 JD 结构化抽取器。

    将 JD 原文发送给大模型，抽取必备技能（含 critical 标记与原文 evidence）、
    岗位职责与资历档位。不返回半成品：校验通过才返回，否则抛 JDExtractionError。
    """

    version: str = "jd-extractor-v1"

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway
        self.token_usage: dict[str, Any] = {}  # 本次调用的 token 用量
        self.model_info: str = ""  # 使用的模型名称

    async def extract(self, raw_text: str) -> JDExtraction:
        """从 JD 原文抽取结构化要求。"""
        # 截断过长的文本，防止超出模型上下文窗口
        if len(raw_text) > MAX_TEXT_LENGTH:
            raw_text = raw_text[:MAX_TEXT_LENGTH]

        messages = [
            {"role": "system", "content": JD_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": JD_EXTRACTION_USER_PROMPT.format(jd_text=raw_text)},
        ]

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._gateway.complete(
                    messages=messages,
                    response_format={"type": "json_object"},
                )
            except Exception as exc:
                # 网关层异常（网络/鉴权/超时）统一包装，便于调用方按契约处理
                raise JDExtractionError(f"LLM gateway error during JD extraction: {exc}") from exc

            self.token_usage = response.usage
            self.model_info = response.model

            try:
                data = json.loads(response.content)
                return JDExtraction.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "JD extraction attempt %d failed: %s",
                    attempt + 1,
                    str(exc)[:200],
                )
                # 重试时将上次的响应和错误信息加入对话，帮助模型自我修正
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Your previous response had a validation error: {exc}. "
                                "Please fix the JSON and try again. Return ONLY valid JSON."
                            ),
                        }
                    )

        raise JDExtractionError(f"Failed to extract valid JD data after {MAX_RETRIES + 1} attempts: {last_error}")
