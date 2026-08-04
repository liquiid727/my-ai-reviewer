# Agent Templates

Role-specific agent instructions for SpecOS workflows.

Document responsibilities, inputs, outputs, and review gates for each agent role.

## Project Roles

| Role | Configuration | Responsibility |
|---|---|---|
| Backend Agent | `.agents/backend.skill.md` | FastAPI、领域服务、LangGraph 和后端基础设施实现 |
| Frontend Agent | `.agents/frontend.skill.md` | React/Vite 页面、组件、状态和前端 API 集成 |
| Testing Agent | `.agents/testing.skill.md` | 单元测试、集成测试和测试替身 |
| Review Agent | `.agents/review.skill.md` | Feature 完成后的代码评审和整改意见 |
| CI Agent | `.agents/ci.skill.md` | 静态检查、类型检查、架构合规和 CI 门禁 |
| QA Agent | `.agents/qa-agent.skill.md` | 独立质量检测、测试证据、风险分级和合并/发布阻断建议 |

QA Agent 是独立验证角色。它默认不修改实现或测试，不删除失败证据，不放宽门禁；质量报告归档到 `reviews/`，标准化场景结果归档到 `tests/results/`。

QA Agent 的项目知识和提示词位于 `skills/qa-quality-governance/`；规范约束仍以 `rules/` 和 `design/quality-architecture.md` 为准。
