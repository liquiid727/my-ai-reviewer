import json
from unittest.mock import AsyncMock

import pytest

from backend.agents.evaluation_agent import AnswerEvaluationAgent
from backend.domain.interview.schemas import AnswerEvaluation
from backend.infrastructure.llm.providers.base import LLMResponse


def _make_gateway_mock(content: str, model: str = "gpt-4o") -> AsyncMock:
    gateway = AsyncMock()
    gateway.complete = AsyncMock(return_value=LLMResponse(content=content, model=model))
    return gateway


VALID_EVAL = json.dumps(
    {
        "score": 75,
        "feedback": "回答覆盖了核心概念，但缺少实际案例",
        "key_points_hit": ["asyncio 基础", "event loop 概念"],
        "key_points_missed": ["实际项目经验", "性能优化"],
        "needs_followup": True,
        "followup_reason": "候选人对性能优化部分回答不够深入",
        "weight": 0.8,
    }
)


@pytest.mark.asyncio
async def test_evaluate_success():
    gateway = _make_gateway_mock(VALID_EVAL)
    agent = AnswerEvaluationAgent(gateway)

    result = await agent.evaluate(
        question_text="请描述 Python 异步编程",
        expected_points=["asyncio", "event loop", "coroutine"],
        answer_text="Python 的异步编程基于 asyncio 模块...",
    )

    assert isinstance(result, AnswerEvaluation)
    assert result.score == 75
    assert result.needs_followup is True
    assert len(result.key_points_hit) == 2
    assert len(result.key_points_missed) == 2
    assert result.weight == 0.8


@pytest.mark.asyncio
async def test_evaluate_with_previous_answers():
    gateway = _make_gateway_mock(VALID_EVAL)
    agent = AnswerEvaluationAgent(gateway)

    previous = [
        {"followup_round": 0, "answer_text": "first answer", "score": 60, "feedback": "需要更多细节"},
    ]

    await agent.evaluate(
        question_text="请描述 Python 异步编程",
        expected_points=["asyncio"],
        answer_text="补充说明...",
        followup_round=1,
        previous_answers=previous,
    )

    call_args = gateway.complete.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "Previous Rounds" in user_msg
    assert "first answer" in user_msg


@pytest.mark.asyncio
async def test_evaluate_stores_model_info():
    gateway = _make_gateway_mock(VALID_EVAL, model="claude-3-opus")
    agent = AnswerEvaluationAgent(gateway)

    await agent.evaluate(
        question_text="test",
        expected_points=[],
        answer_text="test answer",
    )

    assert agent.model_info == "claude-3-opus"


@pytest.mark.asyncio
async def test_evaluate_score_boundaries():
    low_score = json.dumps(
        {
            "score": 0,
            "feedback": "完全不相关",
            "key_points_hit": [],
            "key_points_missed": ["所有要点"],
            "needs_followup": False,
            "weight": 1.0,
        }
    )
    gateway = _make_gateway_mock(low_score)
    agent = AnswerEvaluationAgent(gateway)

    result = await agent.evaluate(
        question_text="test",
        expected_points=["point1"],
        answer_text="irrelevant answer",
    )

    assert result.score == 0
    assert result.needs_followup is False


@pytest.mark.asyncio
async def test_evaluate_retry_on_invalid_json():
    bad = LLMResponse(content="{broken", model="gpt-4o")
    good = LLMResponse(content=VALID_EVAL, model="gpt-4o")
    gateway = AsyncMock()
    gateway.complete = AsyncMock(side_effect=[bad, good])

    agent = AnswerEvaluationAgent(gateway)
    result = await agent.evaluate(
        question_text="test",
        expected_points=[],
        answer_text="answer",
    )

    assert isinstance(result, AnswerEvaluation)
    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_evaluate_raises_after_max_retries():
    gateway = _make_gateway_mock("not valid json")
    agent = AnswerEvaluationAgent(gateway)

    with pytest.raises(ValueError, match="failed after"):
        await agent.evaluate(
            question_text="test",
            expected_points=[],
            answer_text="answer",
        )
