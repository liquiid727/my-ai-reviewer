import json
from unittest.mock import AsyncMock

import pytest

from backend.agents.question_agent import QuestionGenerationAgent
from backend.domain.interview.schemas import QuestionGenerationOutput
from backend.infrastructure.llm.providers.base import LLMResponse


def _make_gateway_mock(content: str, model: str = "gpt-4o") -> AsyncMock:
    gateway = AsyncMock()
    gateway.complete = AsyncMock(return_value=LLMResponse(content=content, model=model))
    return gateway


VALID_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question_text": "请描述你对 Python 异步编程的理解",
                "stage": "basic",
                "difficulty": "medium",
                "expected_points": ["asyncio", "event loop", "coroutine"],
                "jd_relevance": "JD 要求熟练使用 Python 异步框架",
            },
            {
                "question_text": "解释一下 RESTful API 设计的最佳实践",
                "stage": "basic",
                "difficulty": "easy",
                "expected_points": ["HTTP methods", "status codes", "resource naming"],
                "jd_relevance": "后端开发核心能力",
            },
        ]
    }
)


@pytest.mark.asyncio
async def test_generate_success():
    gateway = _make_gateway_mock(VALID_RESPONSE)
    agent = QuestionGenerationAgent(gateway)

    result = await agent.generate(
        resume_data={"profile": {"name": "Test"}},
        jd_text="Python backend developer",
        count=2,
        experience_level="Mid",
    )

    assert isinstance(result, QuestionGenerationOutput)
    assert len(result.questions) == 2
    assert result.questions[0].stage == "basic"
    assert result.questions[0].difficulty == "medium"
    assert len(result.questions[0].expected_points) == 3
    gateway.complete.assert_called_once()


@pytest.mark.asyncio
async def test_generate_stores_model_info():
    gateway = _make_gateway_mock(VALID_RESPONSE, model="deepseek-chat")
    agent = QuestionGenerationAgent(gateway)

    await agent.generate(
        resume_data={"profile": {"name": "Test"}},
        jd_text="",
        count=2,
    )

    assert agent.model_info == "deepseek-chat"


@pytest.mark.asyncio
async def test_generate_no_jd_uses_fallback():
    gateway = _make_gateway_mock(VALID_RESPONSE)
    agent = QuestionGenerationAgent(gateway)

    await agent.generate(
        resume_data={"profile": {"name": "Test"}},
        jd_text="",
        count=2,
    )

    call_args = gateway.complete.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "No JD provided" in user_msg


@pytest.mark.asyncio
async def test_generate_retry_on_invalid_json():
    bad_response = LLMResponse(content="not json", model="gpt-4o")
    good_response = LLMResponse(content=VALID_RESPONSE, model="gpt-4o")
    gateway = AsyncMock()
    gateway.complete = AsyncMock(side_effect=[bad_response, good_response])

    agent = QuestionGenerationAgent(gateway)
    result = await agent.generate(
        resume_data={"profile": {"name": "Test"}},
        jd_text="Python developer",
        count=2,
    )

    assert isinstance(result, QuestionGenerationOutput)
    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_generate_raises_after_max_retries():
    gateway = _make_gateway_mock("invalid json forever")
    agent = QuestionGenerationAgent(gateway)

    with pytest.raises(ValueError, match="failed after"):
        await agent.generate(
            resume_data={"profile": {"name": "Test"}},
            jd_text="Python developer",
            count=2,
        )

    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_generate_retry_on_validation_error():
    incomplete = json.dumps({"questions": [{"question_text": "Q1"}]})
    gateway = AsyncMock()
    gateway.complete = AsyncMock(
        side_effect=[
            LLMResponse(content=incomplete, model="gpt-4o"),
            LLMResponse(content=VALID_RESPONSE, model="gpt-4o"),
        ]
    )

    agent = QuestionGenerationAgent(gateway)
    result = await agent.generate(
        resume_data={},
        jd_text="test",
        count=2,
    )

    assert len(result.questions) == 2
    assert gateway.complete.call_count == 2
