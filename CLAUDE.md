# CLAUDE.md — AI Interview Platform

## Project Overview

AI 面试平台 MVP：简历上传/解析/评估已完成，正在实现面试问答流程。
- **仓库**: liquiid727/my-ai-reviewer
- **当前阶段**: Phase 1 — MVP Interview Q&A Flow (Issues #1-#10)
- **活跃 Feature**: AIP-001-mvp-interview

## Tech Stack

**Backend**: Python 3.12 / FastAPI / SQLAlchemy 2.x (async) / Celery / LangGraph / Pydantic v2
**Frontend**: React 19 / Vite 8 / TypeScript / Tailwind 4 / Zustand / Recharts / Radix UI
**Infra**: PostgreSQL (asyncpg) / Redis / MinIO / Docker Compose
**LLM**: OpenAI / Anthropic / DeepSeek via LLMGateway (`backend/infrastructure/llm/gateway.py`)
**Package Managers**: uv (backend) / pnpm (frontend)

## Architecture — DDD Strict Layering

```
api/           → HTTP 路由，只调用 application 层
application/   → 业务编排（Service），调用 domain + infrastructure
domain/        → 实体、枚举、Schema（纯业务逻辑，不依赖任何外部）
infrastructure/→ DB、LLM、MinIO、Parser 等外部适配
agents/        → LLM Agent（Question/Evaluation/Followup/Report）
workflow/      → LangGraph 图定义（graphs/ + nodes/）
tasks/         → Celery 异步任务
```

**禁止跨层调用**:
- `api/` 不得直接 import `infrastructure/` 或 `domain/`
- `domain/` 不得 import `application/` 或 `infrastructure/`
- 违反此规则的代码不得合并

## Backend Conventions

- **全异步**: 所有 I/O 必须 `async/await`，禁止 sync 阻塞
- **类型注解**: 所有函数签名必须有完整类型注解
- **Pydantic v2**: 数据验证和 LLM 结构化输出
- **SQLAlchemy 2.x**: 使用 `select()` 新式查询，不用旧式 `session.query()`
- **UUID 主键**: 所有表使用 UUID 作为主键
- **JSONB 列**: 复杂嵌套数据用 JSONB 存储
- **Alembic**: 所有 schema 变更必须有对应迁移文件
- **API Response 格式**: `{"code": 0, "message": "ok", "data": {...}}`（code=0 成功）

### LangGraph Pattern

```python
# Node 函数：输入 state → 返回更新字段的 dict
async def evaluate_node(state: InterviewState) -> dict:
    result = await evaluation_agent.run(state["current_question"], state["current_answer"])
    return {"score": result.score, "feedback": result.feedback}

# Graph 构建
builder = StateGraph(InterviewState)
builder.add_node("evaluate", evaluate_node)
builder.add_conditional_edges("decide", should_followup, {"yes": "followup", "no": "next_question"})
graph = builder.compile()
```

### Agent Structured Output

```python
from pydantic import BaseModel

class EvaluationOutput(BaseModel):
    score: int
    feedback: str
    follow_up_needed: bool

# LLM Gateway 调用（已有封装）
gateway = LLMGateway.from_settings(settings)
result = await gateway.chat(system_prompt, user_prompt, response_model=EvaluationOutput)
```

### Prompt Engineering

- System Prompt 定义 AI 角色 + 约束
- User Prompt 注入候选人信息 + JD + 历史记录
- 输出格式用 Pydantic model 约束，禁止自由文本
- Prompt 文件放在 `infrastructure/llm/prompts/` 下

## Frontend Conventions

- **UI 风格**: Neobrutalism（`border-4 border-border shadow-[4px_4px_0_0_#000] font-black`）
- **状态管理**: Zustand store（每个功能域一个 store）
- **API 调用**: `src/api/client.ts` 的 `apiRequest()` 封装，BASE_URL=/api/v1
- **路由**: react-router v7，路径定义在 `App.tsx`
- **组件库**: Radix UI + 自定义 Neobrutalism 封装（`src/components/ui/`）
- **可复用组件**: ScoreGauge, Badge, Card, Progress, Accordion, Alert 等已存在
- **中文 UI**: 页面文案使用中文

## Existing File Map (Already Implemented)

```
backend/
├── api/v1/resume.py          # 5 个简历 API
├── api/v1/schemas.py          # APIResponse 通用包装
├── application/resume_service/ # 上传 + 去重 + MinIO + Celery
├── domain/resume/             # schemas.py, enums.py, entities.py
├── infrastructure/
│   ├── db/models.py           # 5 张表: User, File, Resume, ResumeEvaluation, LLMConfig
│   ├── db/database.py         # async_session_factory
│   ├── llm/gateway.py         # LLMGateway (from_settings / from_config)
│   ├── llm/prompts/           # extraction.py, evaluation.py
│   ├── parsers/               # pdf/docx/txt/md
│   ├── extractors/            # LLMResumeExtractor
│   ├── evaluators/            # LLMResumeEvaluator
│   ├── classifiers/           # RuleBasedResumeClassifier
│   └── storage/minio_client.py
├── tasks/resume_tasks.py      # 4 个 Celery task 链
└── config.py                  # Settings (pydantic-settings)

frontend/src/
├── api/client.ts, resume.ts, evaluation.ts
├── pages/UploadPage, ResumePage, EvaluationPage, SettingsPage
├── stores/resumeStore.ts
├── components/ui/*.tsx        # Neobrutalism 组件
└── types/resume.ts, evaluation.ts
```

## Testing Strategy

- **单元测试**: `pytest + pytest-asyncio`，Agent 逻辑用 mock LLM
- **集成测试**: `pytest + httpx`，真实 DB
- **Mock LLM 模式**:
  ```python
  @patch("backend.agents.evaluation_agent.llm")
  async def test_evaluation(mock_llm):
      mock_llm.ainvoke = AsyncMock(return_value=EvaluationOutput(score=85, feedback="ok"))
  ```
- **测试 DB**: `postgresql+asyncpg://admin:secret@localhost:5432/ai_interview_test`

## Review Checklist

每个 Issue 完成后必须通过以下检查：

- [ ] DDD 分层无跨层调用
- [ ] 所有公开函数有类型注解
- [ ] 无硬编码字符串（用常量/枚举）
- [ ] 异步函数正确使用 async/await
- [ ] 有对应 Alembic 迁移文件（如涉及 DB）
- [ ] Prompt 有 System + User 分离
- [ ] 结构化输出用 Pydantic 定义
- [ ] LLM 调用有 timeout 和错误处理
- [ ] 核心 Agent 有单元测试（mock LLM）
- [ ] 主要 API 有集成测试

## CI Pipeline (Pre-commit)

```bash
ruff check backend/ --fix && ruff format backend/   # Step 1: Lint
mypy backend/ --ignore-missing-imports               # Step 2: Type check
# Step 3: Architecture compliance (grep 跨层 import)
pytest tests/unit -v                                  # Step 4: Unit tests
pytest --cov=backend tests/ --cov-fail-under=75       # Step 5: Coverage ≥ 75%
```

**阻断规则**: ruff error / mypy error / 架构违规 / 单元测试失败 / 覆盖率 < 75% → 禁止合并

## Dev Commands

```bash
# Backend
cd backend && uv run uvicorn main:app --reload --port 8000
cd backend && uv run celery -A celery_app worker -l info

# Frontend
cd frontend && pnpm dev     # Vite dev server on :5173

# DB
docker compose up -d        # PostgreSQL + Redis + MinIO
cd backend && uv run alembic upgrade head
```

## Current Phase 1 Issues (GitHub #1-#10)

| # | Title | Type | Depends |
|---|-------|------|---------|
| 1 | 面试数据模型 + 领域层 + LangGraph 依赖 | backend/infra | — |
| 2 | Question Generation Agent + Prompt | backend | #1 |
| 3 | Answer Evaluation Agent + Prompt | backend | #1 |
| 4 | Followup & Report Generation Agents + Prompts | backend | #2, #3 |
| 5 | LangGraph 面试流程图 (Interview Graph) | backend | #2, #3, #4 |
| 6 | Interview API 端点 + Celery Report Task | backend | #5 |
| 7 | 前端基础层 (types/api/store) + 路由 + 导航 | frontend | #6 |
| 8 | InterviewPage 聊天式面试页面 | frontend | #7 |
| 9 | InterviewReportPage 面试报告页面 | frontend | #7 |
| 10 | InterviewListPage + ResumePage 面试入口 | frontend | #7 |

## Reference Documents

- PRD: `tasks/prd-interview-qa-flow.md`
- SPEC: `tasks/spec-interview-qa-flow.md`
- Skill 规范: `.agents/*.skill.md`（backend, review, testing, ci, prompt, frontend）
