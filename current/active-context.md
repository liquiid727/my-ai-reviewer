# Active Context

**Last Updated**: 2026-06-25

---

## 当前工作上下文

项目处于初始化阶段，LiteSpec 目录结构已完成搭建。

- 所有设计文档已从 `docs/` 迁移拆分至 `design/`
- 第一个功能 Spec `AIP-001` 已创建
- 尚无任何代码实现

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
