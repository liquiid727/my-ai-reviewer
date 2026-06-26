# Coding Guidelines

## Python 规范

- 版本：Python 3.12
- 全局使用 `async/await`（FastAPI + SQLAlchemy 2.x async）
- 类型注解：所有函数签名必须有类型注解
- 使用 `pydantic v2` 做数据验证

---

## FastAPI 路由组织

```text
api/
├── v1/
│   ├── resume.py       # POST /api/v1/resume/upload
│   ├── interview.py    # POST /api/v1/interview/create
│   ├── question.py
│   └── report.py
└── router.py           # 注册所有路由
```

路由文件结构：
```python
from fastapi import APIRouter

router = APIRouter(prefix="/resume", tags=["resume"])

@router.post("/upload")
async def upload_resume(...) -> ResumeResponse:
    ...
```

---

## DDD 分层规范

```text
domain/        → 实体、值对象、领域服务（无框架依赖）
application/   → 用例编排（调用 domain + infrastructure）
infrastructure/→ 数据库、缓存、LLM、外部 API 实现
api/           → HTTP 层（只做参数解析和响应序列化）
```

**禁止**：`api/` 直接调用 `infrastructure/`，必须经过 `application/`。

---

## LangGraph Node 编写规范

```python
from langgraph.graph import StateGraph
from typing import TypedDict

class InterviewState(TypedDict):
    interview_id: str
    stage: str
    current_question: str
    current_answer: str
    history: list
    score: float

async def evaluate_node(state: InterviewState) -> InterviewState:
    # 1. 从 state 读取输入
    question = state["current_question"]
    answer = state["current_answer"]

    # 2. 调用 LLM
    result = await evaluation_agent.run(question, answer)

    # 3. 返回更新后的 state（只返回变化的字段）
    return {"score": result.score}
```

**约定**：
- Node 函数只做单一职责
- 不在 Node 内直接调用数据库，通过 application service
- State 更新使用返回 dict（非整体替换）

---

## 错误处理

```python
# 应用层异常
class InterviewNotFoundError(Exception): ...
class ResumeParseError(Exception): ...

# API 层统一捕获
@app.exception_handler(InterviewNotFoundError)
async def handle_not_found(request, exc):
    return JSONResponse(status_code=404, content={"code": 1002, "message": str(exc)})
```

---

## 目录结构

```text
backend/
├── api/
├── domain/
├── application/
├── infrastructure/
│   ├── db/
│   ├── cache/
│   ├── vector/
│   ├── storage/
│   └── llm/
├── workflow/        # LangGraph Graph 定义
├── agents/          # Agent 实现
├── rag/
├── memory/
├── evaluation/
├── sandbox/
├── multimodal/
└── tests/
```
