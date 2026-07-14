# SPEC: MVP 面试问答流程

> Technical specification derived from: `tasks/prd-interview-qa-flow.md`
> Generated: 2026-07-14 | Target branch: `feat/interview-qa`

## 1. Summary

### 1.1 What This SPEC Covers

实现 MVP 面试问答的完整技术方案：使用 LangGraph 编排面试流程（checkpoint 中断/恢复模式处理人机交互），4 张新数据表存储面试全量数据，6 个 API 端点驱动前后端交互，3 个前端新页面（聊天式面试、面试报告、面试列表），4 套 LLM Prompt 模板（出题、评分、追问、报告）。

### 1.2 PRD Reference

- Source: `tasks/prd-interview-qa-flow.md`
- User Stories covered: US-001 ~ US-008
- Functional Requirements covered: FR-1 ~ FR-12

### 1.3 Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 面试流程编排 | LangGraph + checkpoint 中断恢复 | 原生支持 human-in-the-loop，状态自动持久化，为 Phase 2 多阶段路由打基础 |
| 数据存储 | 4 张独立表 | interviews / interview_questions / question_answers / interview_reports，每轮回答独立行，便于追问权重计算和审计 |
| 前端状态 | Zustand interviewStore | 与已有 resumeStore 模式一致 |
| 报告生成 | Celery 异步任务 | 与已有简历流水线模式一致，避免 API 阻塞 |
| 追问评分权重 | LLM 动态分配 | 评分时 LLM 输出 weight 字段，最终得分 = Σ(score_i × weight_i) |
| 题目优先级 | JD 优先 → 简历补充 | 提供 JD 时至少 60% 题目直接对应 JD 核心要求 |

---

## 2. Architecture

### 2.1 System Context

```
┌─────────────┐     HTTP/JSON      ┌──────────────┐
│  React SPA  │ ◄──────────────── │   FastAPI     │
│  (Vite)     │ ──────────────► │   API Layer   │
└─────────────┘                    └──────┬───────┘
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                      ┌──────────┐ ┌───────────┐ ┌────────┐
                      │LangGraph │ │  Celery    │ │ LLM    │
                      │Interview │ │  Worker    │ │Gateway │
                      │  Graph   │ │(report gen)│ │        │
                      └────┬─────┘ └─────┬─────┘ └────────┘
                           │             │
                      ┌────▼─────────────▼────┐
                      │     PostgreSQL         │
                      │  (data + checkpoints)  │
                      └────────────────────────┘
```

### 2.2 Component Design

| Component | Responsibility |
|-----------|----------------|
| `workflow/graphs/interview_graph.py` | LangGraph 图定义、节点连接、条件路由 |
| `workflow/nodes/*.py` | 6 个图节点函数（analyze、generate、present、evaluate、followup、next） |
| `workflow/state.py` | InterviewState TypedDict 定义 |
| `agents/*_agent/` | 4 个 Agent 实现（封装 Prompt + LLM 调用） |
| `api/v1/interview.py` | 6 个 API 端点 |
| `tasks/interview_tasks.py` | Celery 报告生成任务 |
| `infrastructure/llm/prompts/interview/` | 4 套 Prompt 模板 |

### 2.3 LangGraph 流程

```
START
  │
  ▼
┌─────────────────┐
│ analyze_resume   │  加载简历 parsed_result 到 state
└────────┬────────┘
         ▼
┌─────────────────┐
│generate_questions│  LLM 生成 N 题，写入 DB
└────────┬────────┘
         ▼
┌─────────────────┐
│ present_question │ ◄───────────────────────────┐
│   (interrupt)    │  中断，返回当前题目给用户       │
└────────┬────────┘                              │
         │  ← resume(answer_text)                │
         ▼                                       │
┌─────────────────┐                              │
│ evaluate_answer  │  LLM 评分 + 追问判断          │
└────────┬────────┘                              │
         ▼                                       │
┌─────────────────┐                              │
│ decide_next      │  条件路由 ─────────┐          │
└────────┬────────┘               │          │
    ┌────┼─────────┐              │          │
    ▼    ▼         ▼              │          │
 followup next_q  finish          │          │
    │    │         │              │          │
    │    └─────────┼──────────────┘──────────┘
    └──────────────┘
         │ (finish)
         ▼
       END  → 触发 Celery report task
```

### 2.4 File Structure

```
backend/
├── workflow/
│   ├── __init__.py
│   ├── state.py                          [NEW] InterviewState
│   ├── checkpointer.py                   [NEW] AsyncPostgresSaver 初始化
│   ├── graphs/
│   │   ├── __init__.py
│   │   └── interview_graph.py            [NEW] 图定义
│   └── nodes/
│       ├── __init__.py
│       ├── analyze_resume.py             [NEW]
│       ├── generate_questions.py         [NEW]
│       ├── present_question.py           [NEW]
│       ├── evaluate_answer.py            [NEW]
│       └── decide_next.py               [NEW]
├── agents/
│   ├── question_agent/__init__.py        [IMPL] QuestionGenerationAgent
│   ├── followup_agent/__init__.py        [IMPL] FollowupGenerationAgent
│   ├── evaluation_agent/__init__.py      [IMPL] AnswerEvaluationAgent
│   └── report_agent/__init__.py          [IMPL] ReportGenerationAgent
├── api/v1/
│   ├── interview.py                      [NEW]  6 个端点
│   ├── router.py                         [MOD]  注册 interview_router
│   └── schemas.py                        [MOD]  新增 Interview 相关 schema
├── domain/interview/
│   ├── __init__.py                       [MOD]
│   ├── enums.py                          [NEW]  InterviewStatus 等
│   └── schemas.py                        [NEW]  Pydantic 模型
├── infrastructure/
│   ├── db/models.py                      [MOD]  新增 4 张表
│   └── llm/prompts/
│       ├── question_gen.py               [NEW]
│       ├── answer_eval.py                [NEW]
│       ├── followup_gen.py               [NEW]
│       └── report_gen.py                 [NEW]
├── tasks/
│   └── interview_tasks.py                [NEW]  Celery report task
└── pyproject.toml                        [MOD]  新增 langgraph 依赖

frontend/src/
├── pages/
│   ├── InterviewPage.tsx                 [NEW]
│   ├── InterviewReportPage.tsx           [NEW]
│   └── InterviewListPage.tsx             [NEW]
├── api/interview.ts                      [NEW]
├── stores/interviewStore.ts              [NEW]
├── types/interview.ts                    [NEW]
├── components/Layout.tsx                 [MOD]  导航栏加 Interviews 入口
├── pages/ResumePage.tsx                  [MOD]  加"开始面试"按钮
└── App.tsx                               [MOD]  加 3 条路由
```

---

## 3. Data Model

### 3.1 Schema Changes — 4 张新表

```sql
-- 面试会话表
CREATE TABLE interviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id       UUID NOT NULL REFERENCES resumes(id),
    jd_text         TEXT,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    question_count  INTEGER NOT NULL DEFAULT 5,
    graph_thread_id VARCHAR(100),           -- LangGraph checkpoint thread_id
    config          JSONB DEFAULT '{}',     -- 预留配置项
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_interviews_resume ON interviews(resume_id);
CREATE INDEX ix_interviews_status ON interviews(status);

-- 面试题目表
CREATE TABLE interview_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id    UUID NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    sequence_num    INTEGER NOT NULL,       -- 题号 1,2,3...
    question_text   TEXT NOT NULL,
    stage           VARCHAR(30) NOT NULL,   -- basic/project/architecture/behavior
    difficulty      VARCHAR(20) NOT NULL,   -- easy/medium/hard
    expected_points JSONB DEFAULT '[]',     -- 参考答案要点
    jd_relevance    TEXT,                   -- 对应的 JD 要求
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(interview_id, sequence_num)
);

-- 回答记录表（含追问）
CREATE TABLE question_answers (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id      UUID NOT NULL REFERENCES interview_questions(id) ON DELETE CASCADE,
    answer_text      TEXT NOT NULL,
    is_followup      BOOLEAN NOT NULL DEFAULT false,
    followup_round   INTEGER NOT NULL DEFAULT 0,   -- 0=首轮, 1=追问第1轮, 2=追问第2轮
    followup_question TEXT,                         -- 追问题目文本 (is_followup=true 时)
    score            FLOAT,
    feedback         TEXT,
    key_points_hit   JSONB DEFAULT '[]',
    key_points_missed JSONB DEFAULT '[]',
    weight           FLOAT DEFAULT 1.0,             -- LLM 动态分配的权重
    needs_followup   BOOLEAN DEFAULT false,
    raw_llm_response JSONB,                         -- 原始 LLM 响应（审计用）
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_answers_question ON question_answers(question_id);

-- 面试报告表
CREATE TABLE interview_reports (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id         UUID NOT NULL REFERENCES interviews(id) ON DELETE CASCADE UNIQUE,
    overall_score        FLOAT NOT NULL,
    dimension_scores     JSONB NOT NULL DEFAULT '[]',
    per_question_summary JSONB NOT NULL DEFAULT '[]',
    strengths            JSONB NOT NULL DEFAULT '[]',
    weaknesses           JSONB NOT NULL DEFAULT '[]',
    recommendation       VARCHAR(20) NOT NULL,  -- strong_yes/yes/maybe/no/strong_no
    summary              TEXT,
    llm_model            VARCHAR(100),
    created_at           TIMESTAMPTZ DEFAULT now()
);
```

### 3.2 ORM Model（追加到 `infrastructure/db/models.py`）

```python
class InterviewModel(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    graph_thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    resume: Mapped["ResumeModel"] = relationship(lazy="selectin")
    questions: Mapped[list["InterviewQuestionModel"]] = relationship(
        back_populates="interview", lazy="selectin", order_by="InterviewQuestionModel.sequence_num"
    )
    report: Mapped["InterviewReportModel | None"] = relationship(back_populates="interview", uselist=False, lazy="selectin")


class InterviewQuestionModel(Base):
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_points: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    jd_relevance: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["InterviewModel"] = relationship(back_populates="questions")
    answers: Mapped[list["QuestionAnswerModel"]] = relationship(
        back_populates="question", lazy="selectin", order_by="QuestionAnswerModel.followup_round"
    )


class QuestionAnswerModel(Base):
    __tablename__ = "question_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_followup: Mapped[bool] = mapped_column(default=False)
    followup_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    followup_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points_hit: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    key_points_missed: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    needs_followup: Mapped[bool] = mapped_column(default=False)
    raw_llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question: Mapped["InterviewQuestionModel"] = relationship(back_populates="answers")


class InterviewReportModel(Base):
    __tablename__ = "interview_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    per_question_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    strengths: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    weaknesses: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["InterviewModel"] = relationship(back_populates="report")
```

### 3.3 Enums (`domain/interview/enums.py`)

```python
class InterviewStatus(str, Enum):
    PENDING = "pending"              # 已创建，未开始
    GENERATING = "generating"        # 正在生成题目
    IN_PROGRESS = "in_progress"      # 面试进行中
    REPORT_GENERATING = "report_generating"  # 正在生成报告
    COMPLETED = "completed"          # 面试完成
    FAILED = "failed"                # 失败

class QuestionStage(str, Enum):
    BASIC = "basic"
    PROJECT = "project"
    ARCHITECTURE = "architecture"
    BEHAVIOR = "behavior"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Recommendation(str, Enum):
    STRONG_YES = "strong_yes"
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"
    STRONG_NO = "strong_no"
```

### 3.4 Migration Plan

- 用 Alembic 生成 migration：`alembic revision --autogenerate -m "add interview tables"`
- 4 张表均为新增，无 breaking changes
- LangGraph checkpoint 表由 `AsyncPostgresSaver.setup()` 自动创建（`checkpoints` + `checkpoint_writes` + `checkpoint_blobs`）

---

## 4. API Design

### 4.1 Endpoints

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/api/v1/interview/create` | 创建面试 | `CreateInterviewReq` | `APIResponse<InterviewCreatedData>` |
| POST | `/api/v1/interview/{id}/start` | 开始面试（生成题目+返回第一题） | — | `APIResponse<QuestionPresentData>` |
| POST | `/api/v1/interview/{id}/answer` | 提交回答 | `SubmitAnswerReq` | `APIResponse<AnswerResultData>` |
| GET | `/api/v1/interview/{id}/report` | 获取报告 | — | `APIResponse<InterviewReportData>` |
| GET | `/api/v1/interview/{id}/status` | 查询面试状态 | — | `APIResponse<InterviewStatusData>` |
| GET | `/api/v1/interview/list` | 面试列表 | `?resume_id=` | `APIResponse<list[InterviewListItem]>` |

### 4.2 Request/Response Schemas

```python
# ── Requests ──

class CreateInterviewReq(BaseModel):
    resume_id: uuid.UUID
    jd_text: str | None = None
    question_count: int = Field(default=5, ge=3, le=10)

class SubmitAnswerReq(BaseModel):
    question_id: uuid.UUID
    answer_text: str = Field(min_length=10, max_length=10000)

# ── Responses ──

class InterviewCreatedData(BaseModel):
    interview_id: str
    status: str

class QuestionPresentData(BaseModel):
    question_id: str
    question_text: str
    stage: str                      # basic/project/architecture/behavior
    difficulty: str                 # easy/medium/hard
    current_num: int                # 当前题号 (1-based)
    total_count: int                # 总题数
    is_followup: bool = False
    followup_round: int = 0

class AnswerResultData(BaseModel):
    score: float                    # 0-100
    feedback: str
    key_points_hit: list[str]
    key_points_missed: list[str]
    next: QuestionPresentData | None  # None = 面试结束
    is_finished: bool

class InterviewReportData(BaseModel):
    interview_id: str
    overall_score: float
    dimension_scores: list[dict]    # [{name, score, reason}]
    per_question_summary: list[dict]
    strengths: list[dict]
    weaknesses: list[dict]
    recommendation: str
    summary: str | None
    llm_model: str | None
    created_at: datetime

class InterviewStatusData(BaseModel):
    interview_id: str
    status: str
    current_question_num: int | None
    total_questions: int | None
    answered_count: int

class InterviewListItem(BaseModel):
    interview_id: str
    resume_id: str
    status: str
    question_count: int
    overall_score: float | None     # 已完成时有值
    recommendation: str | None
    created_at: datetime
```

### 4.3 Error Responses

| Error Code | HTTP Status | Condition |
|------------|-------------|-----------|
| `RESUME_NOT_READY` | 400 | resume 未处理完成 (status != evaluated/classified) |
| `INTERVIEW_NOT_FOUND` | 404 | interview_id 不存在 |
| `INTERVIEW_NOT_PENDING` | 400 | start 时 interview 不在 pending 状态 |
| `INTERVIEW_NOT_IN_PROGRESS` | 400 | answer 时 interview 不在 in_progress 状态 |
| `QUESTION_NOT_FOUND` | 404 | question_id 不属于此面试 |
| `QUESTION_ALREADY_ANSWERED` | 400 | 该题已完成所有回答轮次 |
| `ANSWER_TOO_SHORT` | 400 | answer_text < 10 字符 |
| `REPORT_NOT_READY` | 202 | 报告正在生成中 |
| `REPORT_NOT_FOUND` | 404 | 面试未完成，无报告 |

---

## 5. Business Logic

### 5.1 LangGraph State

```python
# workflow/state.py
from typing import TypedDict

class QuestionItem(TypedDict):
    question_id: str
    question_text: str
    stage: str
    difficulty: str
    expected_points: list[str]
    jd_relevance: str | None

class AnswerRecord(TypedDict):
    question_id: str
    answer_text: str
    is_followup: bool
    followup_round: int
    score: float
    feedback: str
    key_points_hit: list[str]
    key_points_missed: list[str]
    weight: float
    needs_followup: bool

class InterviewState(TypedDict):
    # 输入
    interview_id: str
    resume_id: str
    resume_data: dict           # CandidateProfile + classification
    jd_text: str
    question_count: int

    # 题目
    questions: list[QuestionItem]
    current_question_index: int

    # 回答与评分
    answers: list[AnswerRecord]
    current_followup_count: int
    pending_followup: str | None    # 追问题目文本

    # 控制
    is_finished: bool
```

### 5.2 Node Implementation（伪代码）

```python
# ── analyze_resume ──
def analyze_resume(state: InterviewState) -> dict:
    # 从 DB 加载 resume.parsed_result
    session = get_sync_session()
    resume = session.get(ResumeModel, state["resume_id"])
    return {
        "resume_data": resume.parsed_result,
    }

# ── generate_questions ──
def generate_questions(state: InterviewState) -> dict:
    agent = QuestionGenerationAgent(LLMGateway.from_settings())
    questions = agent.generate(
        resume_data=state["resume_data"],
        jd_text=state["jd_text"],
        count=state["question_count"],
    )
    # 写入 DB interview_questions 表
    save_questions_to_db(state["interview_id"], questions)
    # 更新 interview status
    update_interview_status(state["interview_id"], "in_progress")
    return {
        "questions": questions,
        "current_question_index": 0,
        "current_followup_count": 0,
        "pending_followup": None,
    }

# ── present_question ──
def present_question(state: InterviewState) -> dict:
    idx = state["current_question_index"]
    question = state["questions"][idx]
    followup = state.get("pending_followup")

    if followup:
        # 中断：等待追问回答
        answer_text = interrupt({
            "type": "followup",
            "followup_question": followup,
            "followup_round": state["current_followup_count"],
            "question": question,
            "current_num": idx + 1,
            "total_count": len(state["questions"]),
        })
    else:
        # 中断：等待主题回答
        answer_text = interrupt({
            "type": "question",
            "question": question,
            "current_num": idx + 1,
            "total_count": len(state["questions"]),
        })

    return {"_current_answer_text": answer_text}

# ── evaluate_answer ──
def evaluate_answer(state: InterviewState) -> dict:
    idx = state["current_question_index"]
    question = state["questions"][idx]
    answer_text = state["_current_answer_text"]
    is_followup = state.get("pending_followup") is not None
    round_num = state["current_followup_count"] if is_followup else 0

    agent = AnswerEvaluationAgent(LLMGateway.from_settings())
    result = agent.evaluate(
        question=question,
        answer_text=answer_text,
        is_followup=is_followup,
        previous_answers=[a for a in state["answers"] if a["question_id"] == question["question_id"]],
    )

    # 保存回答到 DB
    answer_record = AnswerRecord(
        question_id=question["question_id"],
        answer_text=answer_text,
        is_followup=is_followup,
        followup_round=round_num,
        score=result["score"],
        feedback=result["feedback"],
        key_points_hit=result["key_points_hit"],
        key_points_missed=result["key_points_missed"],
        weight=result["weight"],
        needs_followup=result["needs_followup"],
    )
    save_answer_to_db(answer_record)

    return {
        "answers": [*state["answers"], answer_record],
        "_evaluation": result,
    }

# ── decide_next (条件路由函数) ──
def decide_next(state: InterviewState) -> str:
    evaluation = state["_evaluation"]
    idx = state["current_question_index"]
    followup_count = state["current_followup_count"]

    if evaluation["needs_followup"] and followup_count < 2:
        return "generate_followup"
    elif idx + 1 < len(state["questions"]):
        return "next_question"
    else:
        return "finish"

# ── generate_followup (节点) ──
def generate_followup(state: InterviewState) -> dict:
    idx = state["current_question_index"]
    question = state["questions"][idx]
    prev_answers = [a for a in state["answers"] if a["question_id"] == question["question_id"]]

    agent = FollowupGenerationAgent(LLMGateway.from_settings())
    followup_text = agent.generate(question=question, answers=prev_answers)

    return {
        "pending_followup": followup_text,
        "current_followup_count": state["current_followup_count"] + 1,
    }

# ── next_question (节点) ──
def next_question(state: InterviewState) -> dict:
    return {
        "current_question_index": state["current_question_index"] + 1,
        "current_followup_count": 0,
        "pending_followup": None,
    }

# ── finish (节点) ──
def finish(state: InterviewState) -> dict:
    # 触发 Celery 报告生成
    update_interview_status(state["interview_id"], "report_generating")
    generate_report_task.delay(state["interview_id"])
    return {"is_finished": True}
```

### 5.3 Graph Build

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

builder = StateGraph(InterviewState)

builder.add_node("analyze_resume", analyze_resume)
builder.add_node("generate_questions", generate_questions)
builder.add_node("present_question", present_question)
builder.add_node("evaluate_answer", evaluate_answer)
builder.add_node("generate_followup", generate_followup)
builder.add_node("next_question", next_question)
builder.add_node("finish", finish_interview)

builder.add_edge(START, "analyze_resume")
builder.add_edge("analyze_resume", "generate_questions")
builder.add_edge("generate_questions", "present_question")
builder.add_edge("present_question", "evaluate_answer")
builder.add_conditional_edges("evaluate_answer", decide_next, {
    "generate_followup": "generate_followup",
    "next_question": "next_question",
    "finish": "finish",
})
builder.add_edge("generate_followup", "present_question")
builder.add_edge("next_question", "present_question")
builder.add_edge("finish", END)

checkpointer = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
graph = builder.compile(checkpointer=checkpointer)
```

### 5.4 API ↔ LangGraph 交互

```python
# POST /interview/{id}/start
async def start_interview(interview_id):
    interview = await get_interview(interview_id)
    thread_id = str(interview_id)
    config = {"configurable": {"thread_id": thread_id}}

    # 首次 invoke：图运行到 present_question 中断
    result = await graph.ainvoke(
        {
            "interview_id": str(interview_id),
            "resume_id": str(interview.resume_id),
            "jd_text": interview.jd_text or "",
            "question_count": interview.question_count,
            "questions": [],
            "current_question_index": 0,
            "answers": [],
            "current_followup_count": 0,
            "pending_followup": None,
            "is_finished": False,
        },
        config=config,
    )

    # result 包含中断时返回的 question 数据
    # 从 graph state 中提取 interrupt value
    state = await graph.aget_state(config)
    interrupt_value = state.tasks[0].interrupts[0].value
    return build_question_response(interrupt_value)


# POST /interview/{id}/answer
async def submit_answer(interview_id, answer_req):
    thread_id = str(interview_id)
    config = {"configurable": {"thread_id": thread_id}}

    # 用回答恢复图执行
    result = await graph.ainvoke(
        Command(resume=answer_req.answer_text),
        config=config,
    )

    state = await graph.aget_state(config)

    # 判断图是否已完成
    if state.values.get("is_finished"):
        return AnswerResultData(
            score=last_answer_score,
            feedback=last_answer_feedback,
            next=None,
            is_finished=True,
        )

    # 还有下一题/追问：从 interrupt 中取
    interrupt_value = state.tasks[0].interrupts[0].value
    return build_answer_result(last_evaluation, interrupt_value)
```

### 5.5 评分加权算法

每道题的最终得分由 LLM 动态分配权重：

```python
def compute_question_final_score(answers: list[QuestionAnswerModel]) -> float:
    """计算单题最终加权得分。
    
    LLM 在评分时为每轮回答分配 weight (0.0-1.0)。
    如果只有首轮回答，weight=1.0。
    如果有追问，LLM 根据追问回答质量动态调整：
    - 追问回答优秀：追问权重更高（如首轮0.3 + 追问0.7）
    - 追问回答差：首轮权重更高（如首轮0.7 + 追问0.3）
    
    权重归一化后加权求和。
    """
    total_weight = sum(a.weight for a in answers)
    if total_weight == 0:
        return 0.0
    return sum(a.score * a.weight / total_weight for a in answers)
```

### 5.6 Edge Cases

| Case | Handling |
|------|----------|
| LLM 出题返回数量不足 | 重试 1 次；仍不足则以实际数量进行面试 |
| LLM 评分返回格式错误 | JSON 解析重试（同已有 extractor 模式），最多 1 次 |
| 追问 2 轮后 LLM 仍要求追问 | 强制进入下一题（`followup_count >= 2` 硬限制） |
| 同一题重复提交回答 | 检查该题是否已有非追问回答且无 pending followup，返回 400 |
| 面试中 LLM 调用失败 | graph 异常冒泡到 API 层，返回 500，interview status 保持 in_progress（checkpoint 保证可恢复） |

---

## 6. LLM Prompt Design

### 6.1 Question Generation (`prompts/question_gen.py`)

```python
QUESTION_GEN_SYSTEM_PROMPT = """\
You are a senior technical interviewer. Generate interview questions based on the job description and candidate's resume.

## Priority Rules
1. JD-first: At least 60% of questions MUST directly test skills, tools, or responsibilities mentioned in the JD.
2. Resume-augmented: Remaining questions probe the candidate's specific experience (projects, achievements, claimed skills).
3. If no JD is provided, generate all questions based on the resume.

## Question Distribution
Distribute questions across these stages (adjust based on count):
- basic (1-2): Fundamental concepts for the role's core tech stack
- project (1-2): Deep-dive into specific projects from the resume
- architecture (1): System design or architectural decisions
- behavior (0-1): Teamwork, problem-solving, conflict resolution

## Output JSON Schema
{
  "questions": [
    {
      "question_text": "<the interview question>",
      "stage": "basic|project|architecture|behavior",
      "difficulty": "easy|medium|hard",
      "expected_points": ["<point a good answer should cover>", ...],
      "jd_relevance": "<which JD requirement this tests, or null>"
    }
  ]
}

## Rules
1. Questions must be specific and technical, not generic.
2. Adjust difficulty to candidate's experience level (Junior/Mid/Senior/Staff).
3. For project questions, reference specific projects from the resume by name.
4. expected_points should contain 3-5 concrete technical points.
5. Return ONLY the JSON object.
"""

QUESTION_GEN_USER_PROMPT = """\
Generate {count} interview questions.

## Job Description
{jd_text}

## Candidate Profile
{resume_data}

## Candidate Experience Level
{experience_level}
"""
```

### 6.2 Answer Evaluation (`prompts/answer_eval.py`)

```python
ANSWER_EVAL_SYSTEM_PROMPT = """\
You are evaluating a candidate's interview answer. Be fair but rigorous.

## Scoring Guidelines
- 90-100: Exceptional — deep expertise, specific examples, beyond expected points
- 70-89: Good — covers most expected points with reasonable depth
- 50-69: Average — partially correct, lacks depth or specifics
- 30-49: Below average — significant gaps, vague, or incorrect
- 0-29: Poor — irrelevant, empty, or fundamentally wrong

## Dynamic Weight Assignment
Assign a `weight` (0.0-1.0) for this answer round's contribution to the final question score:
- First answer (followup_round=0): default weight=1.0 if no followup will happen
- If followup happens, re-weight retroactively: 
  - If followup answer is BETTER than first → increase followup weight (e.g., first=0.3, followup=0.7)
  - If followup answer is WORSE than first → decrease followup weight (e.g., first=0.7, followup=0.3)
  - If similar quality → equal weights (e.g., 0.5, 0.5)

## Followup Decision
Set needs_followup=true ONLY when:
1. Score < 70 AND the candidate could reasonably elaborate, OR
2. Key expected points are missed that are critical to assess, OR
3. Answer is vague/superficial but shows potential for depth

Set needs_followup=false when:
1. Answer is comprehensive (score >= 70 with all key points hit)
2. Answer shows the candidate clearly doesn't know the topic (score < 30)
3. Already at maximum followup rounds

## Output JSON Schema
{
  "score": <int 0-100>,
  "feedback": "<2-3 sentence evaluation>",
  "key_points_hit": ["<point the candidate addressed>"],
  "key_points_missed": ["<point the candidate missed>"],
  "needs_followup": <bool>,
  "followup_reason": "<why followup is needed, or null>",
  "weight": <float 0.0-1.0>
}

Return ONLY the JSON object.
"""

ANSWER_EVAL_USER_PROMPT = """\
## Question
{question_text}

## Expected Points
{expected_points}

## Candidate's Answer (round {followup_round})
{answer_text}

{previous_context}
"""
```

### 6.3 Followup Generation (`prompts/followup_gen.py`)

```python
FOLLOWUP_GEN_SYSTEM_PROMPT = """\
You are a senior interviewer generating a follow-up question. The candidate's previous answer was insufficient.

## Rules
1. The followup must be SPECIFIC to what the candidate said (or failed to say).
2. Target the missed key points identified in the evaluation.
3. Do not repeat the original question — probe deeper or from a different angle.
4. Keep it concise — one clear question.

## Output JSON Schema
{
  "followup_question": "<the follow-up question text>"
}

Return ONLY the JSON object.
"""

FOLLOWUP_GEN_USER_PROMPT = """\
## Original Question
{question_text}

## Candidate's Answer
{answer_text}

## Evaluation
Score: {score}, Feedback: {feedback}
Key points missed: {key_points_missed}
Followup reason: {followup_reason}
"""
```

### 6.4 Report Generation (`prompts/report_gen.py`)

```python
REPORT_GEN_SYSTEM_PROMPT = """\
You are generating a comprehensive interview report. Synthesize all question-answer pairs and evaluations into an actionable hiring recommendation.

## Dimensions (exactly 5)
Score each dimension 0-100:
1. 技术能力 — Technical depth, correctness, and breadth
2. 项目深度 — Quality of project experience descriptions and problem-solving
3. 系统设计 — Architecture thinking, trade-off analysis, scalability
4. 沟通表达 — Clarity, structure, and articulation of answers
5. 问题解决 — Analytical approach, edge case thinking, creativity

## Recommendation Scale
- strong_yes: Outstanding candidate, immediate hire (overall >= 85)
- yes: Good candidate, recommend proceeding (overall 70-84)
- maybe: Mixed signals, needs further evaluation (overall 55-69)
- no: Below bar, does not recommend (overall 35-54)
- strong_no: Significant concerns (overall < 35)

## Output JSON Schema
{
  "overall_score": <int 0-100>,
  "dimension_scores": [
    {"name": "<dimension>", "score": <int>, "reason": "<justification>"}
  ],
  "per_question_summary": [
    {
      "question_num": <int>,
      "question_text": "<abbreviated>",
      "final_score": <float>,
      "summary": "<1-2 sentence summary of performance>"
    }
  ],
  "strengths": [
    {"point": "<strength>", "evidence": "<from answers>"}
  ],
  "weaknesses": [
    {"point": "<weakness>", "evidence": "<from answers>"}
  ],
  "recommendation": "strong_yes|yes|maybe|no|strong_no",
  "summary": "<3-5 sentence overall assessment with hiring recommendation>"
}

overall_score is a weighted synthesis — weight 技术能力 and 项目深度 more heavily.
Return ONLY the JSON object.
"""

REPORT_GEN_USER_PROMPT = """\
## Interview Data
{interview_data}
"""
```

---

## 7. Security

### 7.1 Input Validation

| Field | Validation |
|-------|-----------|
| `answer_text` | min 10 chars, max 10000 chars, strip leading/trailing whitespace |
| `jd_text` | max 20000 chars, strip |
| `question_count` | 3-10 integer range |
| `resume_id` | must exist in DB and be in evaluated/classified status |
| `question_id` | must belong to the specified interview |

### 7.2 LLM Prompt Injection Mitigation

- 候选人回答文本在传入 Prompt 前用分隔符包裹：`<candidate_answer>...\n</candidate_answer>`
- System prompt 中明确指示 LLM 将答案视为待评估内容，不作为指令执行

---

## 8. Performance

### 8.1 Expected Latency

| Operation | Expected Latency | Bottleneck |
|-----------|-----------------|------------|
| 创建面试 | < 100ms | DB write |
| 开始面试（生成题目） | 5-15s | LLM call |
| 提交回答（评分） | 3-10s | LLM call |
| 提交回答（评分+追问生成） | 5-15s | 2x LLM calls (sequential) |
| 报告生成 | 10-30s | LLM call (async) |

### 8.2 Optimization

- LangGraph checkpoint 使用 PostgreSQL（已有连接池），无需额外 infra
- 评分 + 追问判断合并为单次 LLM 调用（evaluate_answer prompt 同时输出 needs_followup）
- 追问生成是独立 LLM 调用（需要评分结果作为输入，无法合并）
- 报告生成走 Celery，不阻塞 API 响应

### 8.3 Database

- `ix_interviews_resume` — 按简历查面试列表
- `ix_interviews_status` — 按状态筛选
- `ix_answers_question` — 按题目查回答
- `UNIQUE(interview_id, sequence_num)` — 防止重复题号

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Target | Test |
|--------|------|
| `compute_question_final_score` | 单答案 weight=1.0；多答案动态权重归一化；零权重边界 |
| `decide_next` | followup_count < 2 + needs_followup → followup；>= 2 → next；最后一题 → finish |
| Agent prompt 构建 | 验证 JD/resume 正确注入模板 |
| API schema validation | answer_text 长度校验、question_count 范围校验 |

### 9.2 Integration Tests

| Target | Test |
|--------|------|
| `POST /interview/create` | resume 不存在→404；未评估→400；正常创建→200 |
| `POST /interview/{id}/start` | 重复 start→400；正常→返回第一题 |
| `POST /interview/{id}/answer` | 正常评分返回；追问触发；最后一题返回 is_finished |
| LangGraph checkpoint | 中断后恢复，state 完整性 |

### 9.3 Acceptance Criteria Mapping

| US | Test | Type |
|----|------|------|
| US-001 | 创建面试关联简历 | integration |
| US-002 | LLM 生成 N 题、题目写入 DB | integration + mock LLM |
| US-003 | 回答→评分→返回下一题 | integration |
| US-004 | 追问触发→追问回答→权重计算 | unit + integration |
| US-005 | 报告异步生成→完整字段 | integration + Celery |
| US-006 | 面试页面聊天交互 | browser verify |
| US-007 | 报告页面展示 | browser verify |
| US-008 | 面试列表 + 入口 | browser verify |

---

## 10. Implementation Plan

### 10.1 Phases（建议执行顺序）

```
Phase A: 数据基础                   [US-001]
  ├─ A1. 新增 4 张 ORM 表 + Alembic migration
  ├─ A2. domain/interview/ enums + schemas
  └─ A3. pyproject.toml 添加 langgraph 依赖

Phase B: LLM Agents                [US-002, US-003, US-004]
  ├─ B1. QuestionGenerationAgent + prompt
  ├─ B2. AnswerEvaluationAgent + prompt
  ├─ B3. FollowupGenerationAgent + prompt
  └─ B4. ReportGenerationAgent + prompt

Phase C: LangGraph Workflow        [US-002, US-003, US-004]
  ├─ C1. InterviewState + checkpointer 初始化
  ├─ C2. 6 个 workflow nodes
  └─ C3. interview_graph 编译

Phase D: API 端点                  [US-001~005, US-008]
  ├─ D1. interview.py 6 个端点
  ├─ D2. interview_tasks.py Celery task
  └─ D3. router.py 注册

Phase E: 前端页面                  [US-006, US-007, US-008]
  ├─ E1. types + api + store
  ├─ E2. InterviewPage (聊天式)
  ├─ E3. InterviewReportPage
  ├─ E4. InterviewListPage
  └─ E5. Layout 导航 + ResumePage 入口 + App 路由
```

### 10.2 Issue Mapping

| Issue | SPEC Sections | Priority | Depends On |
|-------|--------------|----------|------------|
| A: 数据模型 + 迁移 | 3.1-3.4 | P0 | — |
| B: LLM Agents 实现 | 6.1-6.4 | P0 | A |
| C: LangGraph 面试图 | 5.1-5.6 | P0 | A, B |
| D: API 端点 | 4.1-4.3 | P0 | A, C |
| E: 前端 3 页面 | (PRD US-006~008) | P0 | D |

### 10.3 Dependencies

```
pyproject.toml 新增:
  langgraph >= 0.2.0
  langgraph-checkpoint-postgres >= 2.0.0
```

---

## 11. Open Questions & Risks

### 11.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LangGraph checkpoint 与现有 SQLAlchemy async session 的连接池冲突 | 连接数耗尽 | checkpoint 使用独立连接字符串或共享 pool |
| LLM 单次调用 > 30s 导致 API 超时 | 用户看到 502 | FastAPI 设置 120s timeout；前端增加超时重试 |
| LLM 生成的题目质量不稳定 | 面试体验差 | Prompt 中增加 few-shot examples；后续 Phase 3 用 RAG 题库辅助 |

### 11.2 Assumptions

- LangGraph `interrupt` + `Command(resume=)` API 稳定可用（基于 langgraph >= 0.2）
- PostgreSQL checkpointer 支持与现有 asyncpg 连接池共存
- 前端直接走 HTTP 同步调用（不用 WebSocket），评分延迟 3-10s 可接受
