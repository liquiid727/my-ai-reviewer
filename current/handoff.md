# Handoff

**Last Updated**: 2026-08-05

## 2026-08-05 Celery 运行时交接

已修复 Celery prefork 子进程内 asyncpg 连接跨 event loop 复用的问题。实现、测试、上线和回滚步骤见 [RIP-009 implementation notes](../implementation/RIP-009-resume-privacy/implementation-notes.md)。后续接手者需要先运行定向单测和真实数据库集成测试，再停止并重启旧 worker/beat；旧 worker 不会自动加载新的生命周期 hook。该修复没有数据库迁移。

---

## 当前状态摘要

项目已有可运行的后端、前端和简历处理链路。当前 issue #038 已完成本地实现，等待测试结果确认、评审和发布。

**下一个 Agent 或开发者接手时，请按顺序读取**：

1. `README.md` — 项目总览
2. `current/project-status.md` — 当前阶段和健康状态
3. `current/active-feature.md` — 当前功能 RIP-001 / issue #038
4. `specs/RIP-001-resume-multiformat-parsers/spec.md` — 功能规格
5. `tasks/issues/issue-038-txt-md-encoding-fallback.md` — issue 验收清单
6. `design/architecture.md` — 技术架构
7. `design/coding-guidelines.md` — 编码规范
8. `implementation/RIP-009-resume-privacy/implementation-notes.md` — Celery async runtime 修复与执行步骤

---

## 上次停止位置

完成 `read_text_with_fallback`、相关文档和测试；parser 范围检查已通过，全库 `mypy` 仍受既有 35 个错误阻塞。

## 下一步

保留全库 `mypy` 阻塞记录，先完成 review，再决定是否单独清理既有类型问题后 ship。不要覆盖现有未提交的 Builder/UI 改动。
