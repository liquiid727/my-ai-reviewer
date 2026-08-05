# Agent Interview Platform

企业级 AI 面试平台，以真实业务驱动系统掌握 Agent 工程能力体系。

---

## 项目目标

构建一个完整的 **AI Interview Platform**，支持：

- 简历分析 / JD 分析
- AI 面试 + 动态追问
- 技术 / 项目 / 系统设计评估
- 面试报告生成

同时作为学习项目，系统掌握：

| 技术领域 | 具体内容 |
|---|---|
| Agent Workflow | LangGraph、State Machine |
| RAG | Embedding、Hybrid Search、Rerank |
| Memory | Session Memory、Long-term Profile |
| Evaluation | LLM-as-Judge、Structured Output |
| Multimodal | ASR、TTS、Vision |
| Sandbox | Docker、gVisor、代码执行 |
| Observability | OpenTelemetry、LangSmith |
| SaaS Architecture | Multi-tenant、RBAC、Billing |

---

## 技术栈速览

```text
Frontend:    React + Vite + TypeScript
API:         FastAPI (Python 3.12)
Workflow:    LangGraph
ORM:         SQLAlchemy + Alembic
Cache:       Redis
Database:    PostgreSQL
Vector DB:   Qdrant
Storage:     MinIO
Task Queue:  Celery
LLM:         OpenAI / Claude / DeepSeek
Observability: OpenTelemetry + LangSmith
```

---

## 产品扩展路径

当前：AI Interview Platform
→ AI Recruiter → AI Tutor → AI Coach → AI Sales → AI Customer Service

本质均为：**Workflow + Agent + RAG + Evaluation**

---

## 当前文档入口

当前仓库处于 `GoalSpec` 模式。日常工作以 `current/`、`design/`、`specs/` 和 `implementation/` 为准；历史资料不会替代这些入口。

- 当前状态：[`current/project-status.md`](current/project-status.md)
- 当前功能：[`current/active-feature.md`](current/active-feature.md)
- 稳定架构：[`design/README.md`](design/README.md)
- 路线图：[`specs/roadmap.md`](specs/roadmap.md)
- 功能规格：[`specs/README.md`](specs/README.md)
- Issue 索引：[`specs/issues/README.md`](specs/issues/README.md)
- 当前草稿：[`spec-draft/README.md`](spec-draft/README.md)
- 实现记录：[`implementation/README.md`](implementation/README.md)

## GoalSpec Agent 加载顺序

Agent 开始任何任务前，按以下顺序加载上下文（约 5-10 个文件）：

```
1. README.md                          ← 你在这里
2. current/project-status.md          ← 当前阶段
3. current/active-feature.md          ← 当前功能
4. current/active-tasks.md            ← 进行中任务
5. design/README.md                   ← 稳定设计索引
6. specs/roadmap.md                   ← 路线图与依赖
7. specs/issues/README.md             ← Issue 索引
8. specs/<SPEC-ID>/                   ← 当前功能规格与任务
9. implementation/<SPEC-ID>/          ← 实现交接与验证记录
10. .agents/<role>.skill.md           ← 对应技能文件
```
