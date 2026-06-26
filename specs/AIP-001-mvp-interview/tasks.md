# AIP-001 Tasks

**Feature**: MVP Interview Agent
**Status**: Not Started

---

## Task 列表

### T1 — 项目骨架初始化
- [ ] 创建 `backend/` 目录（DDD 结构）
- [ ] 初始化 `pyproject.toml` + 依赖（fastapi, langgraph, sqlalchemy, alembic, redis, openai, pymupdf）
- [ ] 配置 `.env.example`
- [ ] 创建 `docker-compose.yml`（PostgreSQL + Redis）

---

### T2 — 数据库初始化
- [ ] Alembic 初始化
- [ ] 创建迁移：`users` 表
- [ ] 创建迁移：`resumes` 表
- [ ] 创建迁移：`interviews` 表
- [ ] 创建迁移：`questions` 表
- [ ] 创建迁移：`answers` 表
- [ ] 创建迁移：`evaluations` 表
- [ ] 创建迁移：`reports` 表

---

### T3 — Resume Service
- [ ] `infrastructure/storage/file_storage.py`（MinIO 或本地）
- [ ] `infrastructure/llm/resume_parser.py`（PyMuPDF 解析 PDF）
- [ ] `agents/resume_agent.py`（LLM 提取 skills + projects）
- [ ] `domain/resume/`（Resume 实体 + Repository）
- [ ] `application/resume_service.py`（上传 + 解析 + 存储）
- [ ] `api/v1/resume.py`（`POST /upload` 路由）

---

### T4 — Interview Service
- [ ] `domain/interview/`（Interview 实体 + Repository）
- [ ] `application/interview_service.py`（创建面试）
- [ ] `api/v1/interview.py`（`POST /create` 路由）

---

### T5 — Question Agent
- [ ] `agents/question_agent.py`（基于 resume + JD 生成题目）
- [ ] `domain/question/`（Question 实体 + Repository）
- [ ] 集成到 LangGraph Node

---

### T6 — Evaluation Agent
- [ ] `agents/evaluation_agent.py`（评分 + feedback，结构化输出）
- [ ] `domain/evaluation/`（Evaluation 实体 + Repository）
- [ ] 集成到 LangGraph Node

---

### T7 — Report Agent
- [ ] `agents/report_agent.py`（汇总生成报告）
- [ ] `domain/report/`（Report 实体 + Repository）
- [ ] 集成到 LangGraph Node

---

### T8 — LangGraph Workflow 串联
- [ ] `workflow/interview_graph.py`（完整 Graph 定义）
- [ ] `workflow/interview_state.py`（InterviewState TypedDict）
- [ ] 连接所有 Node（analyze_resume → generate_questions → loop → generate_report）
- [ ] `application/interview_service.py` 集成 Graph 执行

---

### T9 — 答题 API 接口
- [ ] `POST /api/v1/interview/{id}/start`
- [ ] `POST /api/v1/interview/{id}/answer`
- [ ] `GET /api/v1/interview/{id}/report`

---

### T10 — 验收测试
- [ ] 手动测试完整流程（上传简历 → 5 题 → 评分 → 报告）
- [ ] 单元测试：各 Agent（mock LLM）
- [ ] 集成测试：完整 API 流程

---

## 依赖顺序

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10
```

T3、T4、T5、T6、T7 可在 T2 完成后并行开发。
