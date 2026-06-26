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
Frontend:    Next.js
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

## LiteSpec Agent 加载顺序

Agent 开始任何任务前，按以下顺序加载上下文（约 5-10 个文件）：

```
1. README.md                          ← 你在这里
2. current/project-status.md          ← 当前阶段
3. current/active-feature.md          ← 当前功能
4. current/active-tasks.md            ← 进行中任务
5. design/architecture.md             ← 技术架构
6. design/domain.md                   ← 领域模型
7. design/database.md                 ← 数据库设计
8. design/api-guidelines.md           ← 接口规范
9. specs/AIP-xxx/spec.md              ← 当前功能规格
10. .agents/<role>.skill.md           ← 对应技能文件
```
