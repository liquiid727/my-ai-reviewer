import json
from unittest.mock import AsyncMock

import pytest

from backend.agents.report_agent import ReportGenerationAgent
from backend.domain.interview.schemas import InterviewReport
from backend.infrastructure.llm.providers.base import LLMResponse


def _make_gateway_mock(content: str, model: str = "gpt-4o") -> AsyncMock:
    gateway = AsyncMock()
    gateway.complete = AsyncMock(return_value=LLMResponse(content=content, model=model))
    return gateway


VALID_REPORT = json.dumps(
    {
        "overall_score": 72.5,
        "dimension_scores": [
            {"name": "技术能力", "score": 80, "reason": "对 Python 异步编程有深入理解"},
            {"name": "项目深度", "score": 65, "reason": "项目经验略显单薄"},
            {"name": "系统设计", "score": 70, "reason": "有基本的系统设计思维"},
            {"name": "沟通表达", "score": 75, "reason": "表达清晰有条理"},
            {"name": "问题解决", "score": 72, "reason": "能提出解决方案但不够全面"},
        ],
        "per_question_summary": [
            {
                "question_num": 1,
                "question_text": "描述 Python 异步编程",
                "final_score": 75,
                "summary": "基础概念理解扎实，缺少实战案例",
            },
        ],
        "strengths": [
            {"point": "Python 基础扎实", "evidence": "对 asyncio 和 event loop 机制描述准确"},
        ],
        "weaknesses": [
            {"point": "缺乏大规模项目经验", "evidence": "回答中未提及高并发场景的处理经验"},
        ],
        "recommendation": "yes",
        "summary": "候选人技术基础良好，建议进一步考察大型项目经验。",
    }
)


@pytest.mark.asyncio
async def test_generate_success():
    gateway = _make_gateway_mock(VALID_REPORT)
    agent = ReportGenerationAgent(gateway)

    result = await agent.generate(
        interview_data={
            "questions": [{"question_text": "Q1", "answers": [{"score": 75}]}],
        }
    )

    assert isinstance(result, InterviewReport)
    assert result.overall_score == 72.5
    assert len(result.dimension_scores) == 5
    assert len(result.strengths) == 1
    assert len(result.weaknesses) == 1
    assert result.recommendation == "yes"
    assert result.summary is not None
    gateway.complete.assert_called_once()


@pytest.mark.asyncio
async def test_generate_all_dimensions_have_required_fields():
    gateway = _make_gateway_mock(VALID_REPORT)
    agent = ReportGenerationAgent(gateway)

    result = await agent.generate(interview_data={})

    for dim in result.dimension_scores:
        assert dim.name
        assert 0 <= dim.score <= 100
        assert dim.reason


@pytest.mark.asyncio
async def test_generate_per_question_summary():
    gateway = _make_gateway_mock(VALID_REPORT)
    agent = ReportGenerationAgent(gateway)

    result = await agent.generate(interview_data={})

    assert len(result.per_question_summary) == 1
    q = result.per_question_summary[0]
    assert q.question_num == 1
    assert q.final_score == 75


@pytest.mark.asyncio
async def test_generate_stores_model_info():
    gateway = _make_gateway_mock(VALID_REPORT, model="gpt-4o-mini")
    agent = ReportGenerationAgent(gateway)

    await agent.generate(interview_data={})

    assert agent.model_info == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_generate_retry_on_invalid_json():
    bad = LLMResponse(content="not json", model="gpt-4o")
    good = LLMResponse(content=VALID_REPORT, model="gpt-4o")
    gateway = AsyncMock()
    gateway.complete = AsyncMock(side_effect=[bad, good])

    agent = ReportGenerationAgent(gateway)
    result = await agent.generate(interview_data={})

    assert isinstance(result, InterviewReport)
    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_generate_raises_after_max_retries():
    gateway = _make_gateway_mock("broken")
    agent = ReportGenerationAgent(gateway)

    with pytest.raises(ValueError, match="failed after"):
        await agent.generate(interview_data={})

    assert gateway.complete.call_count == 2


@pytest.mark.asyncio
async def test_generate_score_validation():
    invalid_score = json.dumps(
        {
            "overall_score": 150,
            "dimension_scores": [],
            "per_question_summary": [],
            "strengths": [],
            "weaknesses": [],
            "recommendation": "yes",
        }
    )
    gateway = _make_gateway_mock(invalid_score)
    agent = ReportGenerationAgent(gateway)

    with pytest.raises(ValueError, match="failed after"):
        await agent.generate(interview_data={})


@pytest.mark.asyncio
async def test_generate_recommendation_values():
    for rec in ["strong_yes", "yes", "maybe", "no", "strong_no"]:
        report_data = json.loads(VALID_REPORT)
        report_data["recommendation"] = rec
        gateway = _make_gateway_mock(json.dumps(report_data))
        agent = ReportGenerationAgent(gateway)

        result = await agent.generate(interview_data={})
        assert result.recommendation == rec
