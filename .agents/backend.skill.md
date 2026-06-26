# Backend Skill

适用于所有 Python / FastAPI / LangGraph 开发任务。

---

## 核心原则

1. **DDD 分层**：`api → application → domain → infrastructure`，禁止跨层
2. **全异步**：所有 I/O 操作必须 `async/await`
3. **类型注解**：所有函数签名必须有类型注解
4. **Pydantic v2**：数据验证和结构化输出

---

## FastAPI 模式

```python
# 路由文件结构
from fastapi import APIRouter, Depends
from app.application.resume_service import ResumeService

router = APIRouter(prefix="/resume", tags=["resume"])

@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    return await service.upload(file)
```

---

## LangGraph 模式

```python
from langgraph.graph import StateGraph, END
from app.workflow.interview_state import InterviewState

# Node 函数：输入 state，返回更新的字段
async def evaluate_node(state: InterviewState) -> dict:
    result = await evaluation_agent.run(
        question=state["current_question"],
        answer=state["current_answer"],
    )
    return {"score": result.score, "feedback": result.feedback}

# Graph 构建
builder = StateGraph(InterviewState)
builder.add_node("evaluate", evaluate_node)
builder.add_edge("evaluate", END)
graph = builder.compile()
```

---

## SQLAlchemy 2.x 异步模式

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_interview(session: AsyncSession, interview_id: str) -> Interview:
    result = await session.execute(
        select(Interview).where(Interview.id == interview_id)
    )
    return result.scalar_one_or_none()
```

---

## Agent 结构化输出

```python
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

class EvaluationOutput(BaseModel):
    score: int
    feedback: str

llm = ChatOpenAI(model="gpt-4o")
structured_llm = llm.with_structured_output(EvaluationOutput)
result: EvaluationOutput = await structured_llm.ainvoke(prompt)
```

---

## 常用依赖版本

```toml
fastapi = "^0.115"
langgraph = "^0.2"
sqlalchemy = "^2.0"
alembic = "^1.13"
pydantic = "^2.0"
langchain-openai = "^0.2"
redis = "^5.0"
pymupdf = "^1.24"
python-multipart = "^0.0.9"
```
