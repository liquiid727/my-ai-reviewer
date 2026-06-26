# Architecture

## 系统架构

```text
Frontend (Next.js)
        │
        ▼
FastAPI Gateway
        │
        ▼
Application Layer
        │
        ▼
LangGraph Workflow Engine
        │
        ├── Resume Agent
        ├── Question Agent
        ├── Evaluation Agent
        ├── Followup Agent
        └── Report Agent
        │
        ▼
LLM Gateway
        │
        ├── OpenAI
        ├── Claude
        └── DeepSeek
        │
        ▼
Infrastructure
        ├── PostgreSQL   (主数据库)
        ├── Redis        (缓存 + Session Memory)
        ├── Qdrant       (向量数据库)
        └── MinIO        (对象存储)
```

---

## 技术选型

| 层次 | 技术 | 版本 |
|---|---|---|
| Language | Python | 3.12 |
| API Framework | FastAPI | latest |
| Agent Workflow | LangGraph | latest |
| ORM | SQLAlchemy | 2.x |
| Migration | Alembic | latest |
| Cache | Redis | 7.x |
| Database | PostgreSQL | 16 |
| Vector DB | Qdrant | latest |
| Object Storage | MinIO | latest |
| Async Task | Celery | latest |
| Observability | OpenTelemetry + LangSmith | latest |
| Frontend | Next.js | 14+ |

---

## RAG 设计

### 数据来源
- 技术题库 / 面试题库 / 公司题库 / 岗位知识库

### Qdrant Collection
```text
question_bank
```

### Metadata 结构
```json
{
  "category": "redis",
  "difficulty": "middle",
  "tags": ["cluster"]
}
```

### 检索流程
```text
关键词召回 → 向量召回 → Rerank → Prompt Assemble → LLM
```

---

## Memory 设计

### 短期记忆（Session）
- 存储：Redis
- 内容：当前阶段、当前问题、历史问答

### 长期记忆（Profile）
- 存储：PostgreSQL
- 内容：技能画像、项目画像、弱项画像
```json
{
  "skills": ["Go", "Redis"],
  "weakness": ["System Design"]
}
```

---

## Multimodal 设计

### 支持输入
Text / PDF / DOCX / Voice / Image / Video

### 处理流程
```text
Upload → File Parser → ASR → Vision → Normalize → Agent Workflow
```

### 技术方案
| 场景 | 方案 |
|---|---|
| PDF | PyMuPDF |
| Word | python-docx |
| ASR | Whisper / SenseVoice |
| TTS | OpenAI TTS / CosyVoice |
| Vision | GPT-4o / Qwen-VL / InternVL |

---

## Sandbox 设计

### 支持语言
Python / Go / Java / SQL

### 隔离内容
CPU / Memory / Network / Process / Filesystem

### 执行流程
```text
Code Submit → Sandbox Manager → Create Container → Execute → Collect Result → Destroy
```

### 实现方案
- MVP：Docker
- Production：gVisor / Kata / Firecracker

---

## Evaluation 系统

### 评分维度
| 维度 | 权重 |
|---|---|
| Technical（技术正确性） | 30% |
| Project（项目能力） | 30% |
| Architecture（架构能力） | 20% |
| Communication（表达能力） | 20% |

### 子维度
- Technical：技术正确性
- Engineering：工程深度
- Architecture：架构能力
- Communication：表达能力
- Problem Solving：问题分析能力
