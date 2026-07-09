"""LLM 简历评估器 —— 调用大模型对简历进行多维度评估打分。"""

from __future__ import annotations

import json
from typing import Any

from backend.infrastructure.evaluators.base import ResumeEvaluator
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.prompts.evaluation import (
    RESUME_EVALUATION_SYSTEM_PROMPT,
    RESUME_EVALUATION_USER_PROMPT,
)

VERSION = "llm-evaluator-v1"

# 必须包含的 8 个评估维度
REQUIRED_DIMENSIONS = frozenset([
    "技术能力", "项目质量", "工程能力", "架构能力",
    "业务复杂度", "影响力", "成长性", "AI能力",
])


class LLMResumeEvaluator(ResumeEvaluator):
    """基于 LLM 的简历评估器。

    将结构化简历数据发送给大模型，获取包含综合评分、
    各维度评分、优劣势分析和面试建议的评估报告。
    """

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    @property
    def version(self) -> str:
        return VERSION

    async def evaluate(self, parsed_result: dict) -> dict[str, Any]:
        """执行评估：构建提示词 → 调用 LLM → 解析并验证响应。"""
        resume_text = json.dumps(parsed_result, ensure_ascii=False, indent=2)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": RESUME_EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": RESUME_EVALUATION_USER_PROMPT.format(resume_data=resume_text)},
        ]

        response = await self._gateway.complete(
            messages,
            response_format={"type": "json_object"},
        )

        evaluation = _parse_response(response.content)
        _validate(evaluation)

        # 附加元信息：模型名称、token 用量和评估器版本
        evaluation["_meta"] = {
            "model": response.model,
            "token_usage": response.usage,
            "evaluator_version": VERSION,
        }

        return evaluation


def _parse_response(content: str) -> dict[str, Any]:
    """解析 LLM 返回的 JSON 响应（兼容包裹 markdown 代码块的情况）。"""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc


def _validate(evaluation: dict[str, Any]) -> None:
    """校验评估结果的完整性和合法性。"""
    if "overall_score" not in evaluation:
        raise ValueError("Evaluation missing 'overall_score'")

    score = evaluation["overall_score"]
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        raise ValueError(f"overall_score must be 0-100, got {score}")

    dimensions = evaluation.get("dimension_scores", [])
    if not isinstance(dimensions, list):
        raise ValueError("dimension_scores must be a list")

    # 检查是否包含所有必需的评估维度
    found_names = {d.get("name") for d in dimensions if isinstance(d, dict)}
    missing = REQUIRED_DIMENSIONS - found_names
    if missing:
        raise ValueError(f"Missing required dimensions: {missing}")
