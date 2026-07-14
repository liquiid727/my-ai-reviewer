import json
from unittest.mock import AsyncMock

import pytest

from backend.agents.followup_agent import FollowupGenerationAgent
from backend.domain.interview.schemas import FollowupOutput
from backend.infrastructure.llm.providers.base import LLMResponse


def _make_gateway_mock(content: str, model: str = "gpt-4o") -> AsyncMock:
    gateway = AsyncMock()
    gateway.complete = AsyncMock(return_value=LLMResponse(content=content, model=model))
    return gateway


VALID_FOLLOWUP = json.dumps(
    {
        "followup_question": "你提到了 asyncio，能否具体描述一下你是如何在生产项目中处理并发请求的？",
    }
)


@pytest.mark.asyncio
async def test_generate_success():
    gateway = _make_gateway_mock(VALID_FOLLOWUP)
    agent = FollowupGenerationAgent(gateway)

    result = await agent.generate(
        question_text="描述 Python 异步编程",
        answer_text="asyncio 是 Python 的异步框架...",
        score=65,
        feedback="基础概念正确但缺乏深度",
        key_points_missed=["实际项目经验"],
        followup_reason="需要验证实际应用能力",
    )

    assert isinstance(result, FollowupOutput)
    assert "asyncio" in result.followup_question
    gateway.complete.assert_called_once()


@pytest.mark.asyncio
async def test_generate_without_followup_reason():
    gateway = _make_gateway_mock(VALID_FOLLOWUP)
    agent = FollowupGenerationAgent(gateway)

    await agent.generate(
        question_text="test",
        answer_text="test answer",
        score=50,
        feedback="average",
        key_points_missed=["point1"],
    )

    call_args = gateway.complete.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "N/A" in user_msg


@pytest.mark.asyncio
async def test_generate_stores_model_info():
    gateway = _make_gateway_mock(VALID_FOLLOWUP, model="deepseek-v2")
    agent = FollowupGenerationAgent(gateway)

    await agent.generate(
        question_text="test",
        answer_text="test",
        score=50,
        feedback="ok",
        key_points_missed=[],
    )

    assert agent.model_info == "deepseek-v2"


@pytest.mark.asyncio
async def test_generate_retry_on_invalid_json():
    bad = LLMResponse(content="broken json", model="gpt-4o")
    good = LLMResponse(content=VALID_FOLLOWUP, model="gpt-4o")
    gateway = AsyncMock()
    gateway.complete = AsyncMock(side_effect=[bad, good])

    agent = FollowupGenerationAgent(gateway)
    result = await agent.generate(
        question_text="test",
        answer_text="test",
        score=50,
        feedback="ok",
        key_points_missed=[],
    )

    assert isinstance(result, FollowupOutput)
    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_generate_raises_after_max_retries():
    gateway = _make_gateway_mock("not valid json")
    agent = FollowupGenerationAgent(gateway)

    with pytest.raises(ValueError, match="failed after"):
        await agent.generate(
            question_text="test",
            answer_text="test",
            score=50,
            feedback="ok",
            key_points_missed=[],
        )

    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_generate_passes_key_points_as_json():
    gateway = _make_gateway_mock(VALID_FOLLOWUP)
    agent = FollowupGenerationAgent(gateway)

    missed = ["并发控制", "错误处理", "资源管理"]
    await agent.generate(
        question_text="test",
        answer_text="test",
        score=40,
        feedback="多个要点未覆盖",
        key_points_missed=missed,
    )

    call_args = gateway.complete.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "并发控制" in user_msg
    assert "错误处理" in user_msg
