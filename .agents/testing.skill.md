# Testing Skill

---

## 测试策略

| 层次 | 工具 | 说明 |
|---|---|---|
| 单元测试 | pytest + pytest-asyncio | Agent 逻辑（mock LLM） |
| 集成测试 | pytest + httpx | API 端到端（真实 DB） |
| 手动验收 | curl / Postman | 按 tests.md 执行 |

---

## Mock LLM

```python
from unittest.mock import AsyncMock, patch

@patch("app.agents.evaluation_agent.llm")
async def test_evaluation(mock_llm):
    mock_llm.ainvoke = AsyncMock(return_value=EvaluationOutput(
        score=85, feedback="回答清晰"
    ))
    result = await evaluation_agent.run("问题", "答案")
    assert result.score == 85
```

---

## 测试数据库

集成测试使用独立的测试数据库：

```env
TEST_DATABASE_URL=postgresql+asyncpg://admin:secret@localhost:5432/ai_interview_test
```

每次测试前重置：
```python
@pytest.fixture(autouse=True)
async def reset_db(async_session):
    yield
    await async_session.rollback()
```

---

## 运行测试

```bash
# 单元测试
pytest tests/unit -v

# 集成测试
pytest tests/integration -v

# 全部
pytest --cov=app tests/
```
