# Project Context

**项目名称**：Agent Interview Platform

**类型**：AI Interview Platform + Agent 学习项目

**当前阶段**：Phase 1 — MVP Interview Agent（Not Started）

**活跃 Feature**：`AIP-001-mvp-interview`

---

## Agent 加载顺序

任何任务开始前，按此顺序加载（约 5-10 文件，控制 token 成本）：

```
必读（每次都加载）：
1. README.md
2. current/project-status.md
3. current/active-feature.md

按需加载（根据任务类型）：
4. design/architecture.md       ← 技术架构类任务
5. design/domain.md             ← Agent / Workflow 类任务
6. design/database.md           ← 数据库类任务
7. design/api-guidelines.md     ← API 开发任务
8. design/coding-guidelines.md  ← 编码任务必读

功能上下文（当前 Feature）：
9.  specs/AIP-001-mvp-interview/spec.md
10. specs/AIP-001-mvp-interview/tasks.md

技能文件（按角色）：
11. .agents/backend.skill.md    ← 后端开发
12. .agents/testing.skill.md    ← 测试任务
```

---

## 禁止行为

- 不要跳过 `design/coding-guidelines.md`（分层规范必须遵守）
- 不要直接修改 `docs/`（原始文档，已迁移至各 design/ 文件）
- 不要在 Phase 1 引入 RAG / Sandbox / Multimodal（留给后续 Phase）
