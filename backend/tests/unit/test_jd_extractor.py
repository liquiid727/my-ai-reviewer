"""JD 抽取器单测 —— 正常抽取 / 输出畸形重试成功 / 重试仍失败三路径（mock LLMGateway）。"""

import json
from unittest.mock import AsyncMock

import pytest

from backend.infrastructure.extractors.jd_extractor import (
    MAX_TEXT_LENGTH,
    JDExtractionError,
    JDExtractor,
)
from backend.infrastructure.llm.providers.base import LLMResponse

VALID_EXTRACTION = json.dumps(
    {
        "required_skills": [
            {"name": "Go", "critical": True, "evidence": "精通 Go 语言，3 年以上经验"},
            {"name": "Kubernetes", "critical": False, "evidence": "熟悉 K8s 者优先"},
        ],
        "responsibilities": ["负责核心服务架构设计", "参与代码评审"],
        "seniority": "senior",
    }
)


def _make_gateway_mock(*contents: str, model: str = "gpt-4o") -> AsyncMock:
    """构造按调用次序依次返回 contents 的 mock gateway。"""
    gateway = AsyncMock()
    gateway.complete = AsyncMock(
        side_effect=[LLMResponse(content=c, model=model) for c in contents],
    )
    return gateway


@pytest.mark.asyncio
async def test_extract_success() -> None:
    """正常路径：合法 JSON → JDExtraction，技能带 critical + evidence。"""
    gateway = _make_gateway_mock(VALID_EXTRACTION)
    extractor = JDExtractor(gateway)

    result = await extractor.extract("岗位描述：精通 Go 语言……")

    assert result.seniority == "senior"
    assert result.skill_names == ["Go", "Kubernetes"]
    assert result.critical_skills == ["Go"]
    assert result.required_skills[0].evidence == "精通 Go 语言，3 年以上经验"
    assert result.responsibilities == ["负责核心服务架构设计", "参与代码评审"]
    assert gateway.complete.call_count == 1
    assert extractor.model_info == "gpt-4o"


@pytest.mark.asyncio
async def test_extract_retry_on_invalid_output() -> None:
    """输出畸形（非 JSON）→ 内部重试 1 次成功，且重试消息带上错误提示。"""
    gateway = _make_gateway_mock("not json at all", VALID_EXTRACTION)
    extractor = JDExtractor(gateway)

    result = await extractor.extract("JD text")

    assert result.skill_names == ["Go", "Kubernetes"]
    assert gateway.complete.call_count == 2
    # 第二次调用的消息应包含上次响应与修正提示
    retry_messages = gateway.complete.call_args.kwargs["messages"]
    assert retry_messages[-2]["content"] == "not json at all"
    assert "validation error" in retry_messages[-1]["content"]


@pytest.mark.asyncio
async def test_extract_retry_on_schema_violation() -> None:
    """JSON 合法但 schema 非法（seniority 越界）→ 同样触发重试。"""
    bad_schema = json.dumps({"required_skills": [], "seniority": "principal"})
    gateway = _make_gateway_mock(bad_schema, VALID_EXTRACTION)
    extractor = JDExtractor(gateway)

    result = await extractor.extract("JD text")

    assert result.seniority == "senior"
    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_extract_empty_json_triggers_retry() -> None:
    """空 JSON `{}`（键缺失）不得静默通过 → 触发重试，不返回空结果。"""
    gateway = _make_gateway_mock("{}", VALID_EXTRACTION)
    extractor = JDExtractor(gateway)

    result = await extractor.extract("JD text")

    assert result.skill_names == ["Go", "Kubernetes"]
    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_extract_raises_after_max_retries() -> None:
    """重试后仍不合法 → 抛 JDExtractionError，不返回半成品。"""
    gateway = _make_gateway_mock("broken", "still broken")
    extractor = JDExtractor(gateway)

    with pytest.raises(JDExtractionError, match="after 2 attempts"):
        await extractor.extract("JD text")

    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_extract_truncates_long_text() -> None:
    """超长 JD 文本被截断到 MAX_TEXT_LENGTH，防止超出上下文窗口。"""
    gateway = _make_gateway_mock(VALID_EXTRACTION)
    extractor = JDExtractor(gateway)

    await extractor.extract("x" * (MAX_TEXT_LENGTH + 1000))

    messages = gateway.complete.call_args.kwargs["messages"]
    user_content = messages[1]["content"]
    assert "x" * MAX_TEXT_LENGTH in user_content
    assert "x" * (MAX_TEXT_LENGTH + 1) not in user_content


@pytest.mark.asyncio
async def test_extract_wraps_gateway_error() -> None:
    """网关层异常（网络/鉴权/超时）包装为 JDExtractionError，不穿透裸异常。"""
    gateway = AsyncMock()
    gateway.complete = AsyncMock(side_effect=ConnectionError("connection refused"))
    extractor = JDExtractor(gateway)

    with pytest.raises(JDExtractionError, match="LLM gateway error"):
        await extractor.extract("JD text")
