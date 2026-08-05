# Active Context

**Last Updated**: 2026-08-05

---

## 当前工作上下文

项目已完成基础面试链路、简历解析扩展、Resume Builder 和 LLM 门禁等实现；当前正在收尾 RIP-001 的 TXT/Markdown 编码兜底 issue #038。

- 所有设计文档已从 `docs/` 迁移拆分至 `design/`
- `AIP-001` 已有代码实现，但历史任务清单和评审记录尚未完全回填
- RIP-001 的六格式解析器已接入工厂，#038 已完成本地实现，待评审 / 发布
- Celery prefork 的 asyncpg 跨 loop 故障已完成本地修复：任务共享 PID-owned runner，worker fork 后重置 SQLAlchemy pool；详见 `implementation/RIP-009-resume-privacy/implementation-notes.md`

---

## 关键决策记录

| 决策 | 内容 |
|---|---|
| 项目结构 | LiteSpec 规范，Feature ID 前缀 `AIP-` |
| 后端框架 | FastAPI + LangGraph（Python 3.12） |
| 数据库 | PostgreSQL（主）+ Redis（缓存）+ Qdrant（向量） |
| LLM | 多模型支持（OpenAI / Claude / DeepSeek） |
| 架构模式 | DDD（domain/application/infrastructure） |

---

## 注意事项

- Phase 1 仅实现文字面试，不含语音/视觉
- Phase 1 不含 RAG，问题由 LLM 直接生成
- Phase 1 不含 Sandbox，不含代码题
