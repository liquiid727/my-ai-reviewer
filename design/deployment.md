# Deployment

## 基础设施组件

| 组件 | 用途 | 端口 |
|---|---|---|
| PostgreSQL 16 | 主数据库 | 5432 |
| Redis 7 | 缓存 + Session Memory | 6379 |
| Qdrant | 向量数据库（题库 RAG） | 6333 |
| MinIO | 对象存储（简历文件 / 音频） | 9000 |
| Celery | 异步任务队列（Broker: Redis） | — |

---

## 本地开发（Docker Compose）

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ai_interview
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret

  redis:
    image: redis:7-alpine

  qdrant:
    image: qdrant/qdrant

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
```

---

## Observability

### 工具链
- **OpenTelemetry**：采集 Trace / Metrics / Logs
- **LangSmith**：LangGraph Workflow 专项追踪

### Trace 设计

```text
Trace = 一次完整面试（interview_id）

Spans:
  ├── resume_agent      (简历解析耗时 + token)
  ├── question_agent    (出题耗时 + token)
  ├── evaluation_agent  (评分耗时 + token)
  └── report_agent      (报告生成耗时 + token)
```

### 关键指标

| 指标 | 说明 |
|---|---|
| Latency | 各 Agent 响应时间 |
| Token Usage | 每次 LLM 调用 token 消耗 |
| Cost (USD) | 按 token 计费累计 |
| Error Rate | Agent 失败率 |
| Success Rate | 面试完成率 |

---

## 环境变量

```env
# Database
DATABASE_URL=postgresql+asyncpg://admin:secret@localhost:5432/ai_interview

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# LLM
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# LangSmith
LANGSMITH_API_KEY=ls__xxx
LANGSMITH_PROJECT=ai-interview
```
