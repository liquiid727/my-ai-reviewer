"""LLM 简历润色器的单元测试（mock gateway）。"""

import json
from unittest.mock import AsyncMock

import pytest

from backend.domain.resume.enums import ResumeSectionType
from backend.infrastructure.llm.providers.base import LLMResponse
from backend.infrastructure.polishers.llm_polisher import LLMResumePolisher


def _make_gateway_mock(*contents: str, model: str = "gpt-4o") -> AsyncMock:
    """构造一个按调用次序依次返回 contents 的 mock gateway。"""
    gateway = AsyncMock()
    gateway.complete = AsyncMock(
        side_effect=[LLMResponse(content=c, model=model) for c in contents],
    )
    return gateway


@pytest.mark.asyncio
async def test_polish_success() -> None:
    content = json.dumps({
        "polished_items": ["主导订单系统重构，QPS 提升 3 倍", "设计高可用支付网关"],
        "notes": "动词开头、量化结果",
    })
    gateway = _make_gateway_mock(content)
    polisher = LLMResumePolisher(gateway)

    result = await polisher.polish(
        ResumeSectionType.WORK_EXPERIENCE,
        ["负责订单系统", "做了支付网关"],
    )

    assert result.original_items == ["负责订单系统", "做了支付网关"]
    assert len(result.polished_items) == 2
    assert result.notes == "动词开头、量化结果"
    assert gateway.complete.await_count == 1


@pytest.mark.asyncio
async def test_polish_empty_input_skips_llm() -> None:
    gateway = _make_gateway_mock()
    polisher = LLMResumePolisher(gateway)

    result = await polisher.polish(ResumeSectionType.SKILLS, ["", "   "])

    assert result.polished_items == []
    assert gateway.complete.await_count == 0


@pytest.mark.asyncio
async def test_polish_retries_on_bad_json_then_succeeds() -> None:
    bad = "not json at all"
    good = json.dumps({"polished_items": ["优化后的要点"], "notes": None})
    gateway = _make_gateway_mock(bad, good)
    polisher = LLMResumePolisher(gateway)

    result = await polisher.polish(ResumeSectionType.WORK_EXPERIENCE, ["原始要点"])

    assert result.polished_items == ["优化后的要点"]
    assert gateway.complete.await_count == 2


@pytest.mark.asyncio
async def test_polish_count_mismatch_raises_after_retries() -> None:
    # 返回条目数量始终不匹配（输入 2 条，返回 1 条），重试耗尽后抛错
    wrong = json.dumps({"polished_items": ["只有一条"], "notes": None})
    gateway = _make_gateway_mock(wrong, wrong)
    polisher = LLMResumePolisher(gateway)

    with pytest.raises(ValueError):
        await polisher.polish(ResumeSectionType.WORK_EXPERIENCE, ["a", "b"])
    assert gateway.complete.await_count == 2


@pytest.mark.asyncio
async def test_polish_strips_markdown_fence() -> None:
    fenced = "```json\n" + json.dumps({"polished_items": ["x"], "notes": "n"}) + "\n```"
    gateway = _make_gateway_mock(fenced)
    polisher = LLMResumePolisher(gateway)

    result = await polisher.polish(ResumeSectionType.SKILLS, ["y"])
    assert result.polished_items == ["x"]
