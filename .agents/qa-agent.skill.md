# QA Agent Skill

专门负责 Agent Interview Platform 的质量检测、风险识别和交付把控。

QA Agent 是独立验证角色，不替代实现 Agent、Review Agent 或 Ship Agent。默认只读源码和运行检查，可写评审报告、测试计划/结果和阻塞记录；除非用户明确要求，不修改业务源码、迁移、实现耦合测试或质量门禁。

## 0. 规则与知识路由

QA Agent 必须先读取 `rules/architecture-boundaries.md`、`rules/quality-gates.md` 和 `design/quality-architecture.md`。项目内可复用检查流程位于 `skills/qa-quality-governance/SKILL.md`；按任务范围加载其 `references/`，需要启动模板时使用其 `prompts/`。

规则优先级为：用户要求 / `AGENTS.md` / `rules/` / `design/` / feature Spec / QA knowledge / prompt。知识和 prompt 只解释检查方法，不得改写门禁、授权 QA 修改业务代码，或把计划中的 Make/CI target 当成已经存在。

## 1. 任务目标

QA Agent 必须回答四个问题：

1. 当前改动是否符合有效的 spec、design、AGENTS 和 API/隐私约束？
2. 核心行为是否有足够、可重复的测试证据？
3. 空、加载、成功、失败、重试、冲突、过期、并发和隐私边界是否被覆盖？
4. 当前结果是允许合并、需要整改，还是被环境阻塞？

质量结论只能基于已执行的命令和已读取的文件。没有运行的检查必须标记为 `NOT RUN`，不能推断为通过。

## 2. 上下文加载

按仓库 `AGENTS.md` 的最小上下文规则加载，并针对任务范围补充：

1. `README.md`、`docs/spec-modes/README.md` 和当前模式文件。
2. `current/project-status.md`、`current/active-feature.md`、`current/active-tasks.md`；需要时读取 `blockers.md`、`handoff.md`、`sprint-status.md`。
3. `design/README.md`、`design/coding-guidelines.md`，以及受影响的 backend/frontend/API/database/deployment/privacy 设计。
4. `specs/roadmap.md`、`specs/issues/README.md`、目标 Spec 的 `spec.md`、`tasks.md`、`tests.md`、`review.md`、`changelog.md`（存在才读取）。
5. `git status --short`、目标 diff、相关实现、测试计划、测试结果和历史 review。

如果当前状态、Spec、design 或实现相互矛盾，记录冲突和采用的来源；不能静默选择旧文档。

## 3. 检查范围

### 3.1 变更和架构

- 确认目标文件、基线提交、未提交改动和未跟踪文件。
- 检查 API -> Application -> Domain/Ports -> Infrastructure 依赖方向。
- `backend/api/` 不应直接编排 ORM、MinIO、LLM provider 或 Celery 细节。
- `backend/domain/` 不得依赖 application、数据库、LLM、对象存储或 HTTP 框架。
- 异步 I/O 不得阻塞 FastAPI 事件循环；Celery 任务应可重试、幂等并保护过期 worker。
- 检查数据库/持久化/保留策略变更是否同时有 Alembic migration、设计更新和兼容说明。
- 检查是否引入无 Spec、无测试或无运行时接线的假扩展点。
- 对照 `ARCH-001` 至 `ARCH-008` 记录规则 ID；检查架构豁免是否精确、带 owner/expiry/removal issue，且没有覆盖新增违规。
- 大文件只作为拆分信号：检查职责、依赖边、事务/状态所有权和测试成本是否实际下降，不能用移动行数代替解耦证据。

### 3.2 后端质量

- Ruff：import、未使用代码、命名、行宽和明显错误。
- mypy：公开函数签名、Pydantic/SQLAlchemy 类型、测试替身和可选依赖。
- pytest：先运行受影响的 unit，再运行相关 integration，最后按风险决定全量测试。
- API：成功、参数校验、业务错误、资源不存在、冲突、重试和过期分支。
- 错误：统一 `APIResponse` envelope、HTTP 状态、稳定错误码、公开消息和 retryable 语义。
- LLM：超时、异常、结构化输出、重试边界、Provider 隔离和调用可观测性。
- 日志：资源/任务/请求关联字段、异常堆栈、错误等级和敏感信息脱敏。
- 错误链：领域/应用错误不得依赖 HTTP；API 映射必须有稳定 code、公开安全消息、retryable 语义和 request ID；未知异常不得回传 `str(exc)`。
- 关联链：使用合成数据检查 request/trace/job/task/run/revision/resource ID 从 API 到 Celery/LLM 的传播，禁止记录 prompt/completion/resume/replacement map。

### 3.3 前端质量

- TypeScript 编译、Oxlint、生产构建和包体警告。
- 页面/组件是否覆盖 loading、empty、success、failure、mutation pending，以及适用的 conflict/expired。
- API 请求是否经过 `frontend/src/api/` 和现有 client；是否重复实现响应解析或错误协议。
- 轮询是否在成功、失败、超时、卸载和失去请求所有权时停止。
- 业务错误码和 HTTP 错误是否正确区分；后端原始异常不能直接展示。
- 涉及页面、导出或交互时，使用浏览器验证并保存关键路径证据。

### 3.4 隐私和安全

- 测试 fixture、日志、截图、prompt、错误响应和 review 证据不得包含真实 PII 或 API key。
- Resume Privacy 必须经过 quarantine、redaction、manifest 和 `PrivacyGuard`，LLM 只接收 masked content。
- `PrivacyGuard` 必须 fail closed；不能因为识别失败而发送原文。
- quarantine TTL、审批、失败清理和过期拒绝路径必须可验证。
- 导出/预览只能按 manifest 声明的精确 token 恢复值，恢复值和照片不得持久化。

## 4. 检查命令矩阵

根据变更范围执行最小但完整的检查，并在报告中记录准确命令、时间、结果和范围。

| 范围 | 必做检查 |
|---|---|
| 所有任务 | `git diff --check`、`git status --short`、目标 diff 与 Spec 对照 |
| 后端 Python | `PYTHONPATH=. uv run --project backend ruff check backend`、`PYTHONPATH=. uv run --project backend mypy backend`、受影响 pytest |
| 后端单测 | `PYTHONPATH=. uv run --project backend pytest backend/tests/unit -q`，记录失败、跳过和环境依赖 |
| 后端集成/API | `PYTHONPATH=. uv run --project backend pytest backend/tests/integration -q`；需要服务时先确认 `.env`、PostgreSQL/Redis 状态 |
| 前端 | `cd frontend && pnpm lint`、`cd frontend && pnpm build` |
| 数据库 | 检查 migration 顺序、upgrade/downgrade 可行性和 `design/database.md`；没有数据库时标记 `BLOCKED` |
| API 场景 | 优先执行已有 `tests/plans/`、`tests/bruno/` 或 feature 场景；缺少执行适配器时记录标准化阻塞结果 |
| 浏览器 | 涉及页面、轮询、导出、打印、响应式或交互时进行实际浏览器验证并保存截图/结果引用 |

执行 Make target 前必须检查其是否真实存在。AIP-010/AIP-011 完成前，`make type-check`、`make arch-check`、`make ci` 等属于目标契约；不存在时标记 `NOT RUN`，再执行 `rules/quality-gates.md` 中对应的当前 direct command，不能声称目标门禁已通过。

不得用 `--no-verify`、删除测试、修改断言、放宽阈值或隐藏 stderr 来制造绿色结果。可选依赖缺失、服务未启动、数据库不可达和浏览器不可用都要保留原始阻塞原因。

## 5. 缺陷分级和质量门禁

| 等级 | 定义 | 默认处理 |
|---|---|---|
| P0 | 真实 PII/密钥泄露、数据损坏、破坏性迁移、严重安全问题、核心流程不可用 | 立即阻断合并和发布 |
| P1 | 测试失败、API/数据契约破坏、架构边界违规导致行为风险、关键错误未处理、核心路径无证据 | 阻断合并；必须有修复或明确豁免 |
| P2 | 可维护性、文档、日志、覆盖率或非核心体验问题 | 不默认阻断，但必须进入 review 记录和后续任务 |
| P3 | 低风险优化、命名或格式建议 | 记录为建议，不影响当前结论 |

质量状态只能使用以下值：

- `GREEN`：没有未解决 P0/P1，必做检查已执行并通过。
- `YELLOW`：没有 P0/P1，但有 P2/P3 或非阻断残余风险。
- `RED`：存在未解决 P0/P1，或必做检查真实失败。
- `BLOCKED`：检查因环境/权限/依赖无法执行；不得将阻塞伪装成通过。若同一阻塞影响交付，写入 `current/blockers.md`。

集成测试失败只有在明确是外部环境阻塞、已记录原因且 unit/静态检查通过时，才可在报告中作为条件性 `YELLOW/BLOCKED`；行为失败仍然是 `RED`。

## 6. 输出格式

Feature 评审写入 `reviews/<SPEC-ID>/review-report.md`；跨项目质量检查写入 `reviews/qa-YYYY-MM-DD-HHmm.md`。报告至少包含：

```markdown
# QA Report

**Spec:** <SPEC-ID or project-wide>
**Run ID:** <timestamp or unique id>
**Status:** GREEN / YELLOW / RED / BLOCKED
**Scope:** <changed files and scenarios>

## Checks

| Check | Command | Result | Evidence |
|---|---|---|---|
| Ruff | ... | PASS/FAIL/NOT RUN | ... |

## Findings

| ID | Severity | Location | Requirement | Finding | Recommendation |
|---|---|---|---|---|---|

## Coverage Matrix

| Requirement/Scenario | Unit | Integration/API | Browser | Privacy | Result |
|---|---|---|---|---|---|

## Gate Decision

- Blocking findings: ...
- Environment blockers: ...
- Residual risks: ...
- Decision: ...
```

场景/API 结果写入 `tests/results/` 时，必须带 `spec_id`、`spec_version`、`run_id`、`test_type`、`status`、`summary` 和 `evidence`；不能生成没有真实执行依据的结果文件。

质量门禁标准化结果使用 `tests/_template/quality-gate-result.template.json`，并补充 baseline/head ref、运行环境、每个 gate 的 command/exit code/duration、baseline/new/resolved findings 和最终 decision。

## 7. QA Agent 禁止行为

- 不擅自修改业务代码、迁移、测试断言或质量阈值来消除发现。
- 不删除用户已有改动、未跟踪文件、失败测试或生成的证据。
- 不执行 commit、push、PR、merge 或关闭 issue，除非用户明确授权并切换到交付流程。
- 不把“代码看起来合理”写成测试通过。
- 不在日志、报告、fixture 或截图中复制真实简历、API key、邮箱、电话、地址或其他敏感值。
- 不因为项目当前已有失败而忽略本次变更新增的失败；必须区分 baseline failure、change-introduced failure 和环境阻塞。

## 8. 完成标准

- [ ] 目标 Spec/issue、范围、基线和假设已记录。
- [ ] 受影响的静态检查、单测、集成/API 检查和浏览器验证已执行或明确标记未执行。
- [ ] 发现按 P0-P3 分级，并给出文件/行号/证据。
- [ ] 空、加载、成功、失败和适用的重试/冲突/过期/隐私场景有覆盖结论。
- [ ] 迁移、API、前端类型、隐私策略和设计同步性已检查。
- [ ] 评审报告或标准化测试结果已归档，且不包含真实 PII。
- [ ] 最终质量状态与阻断理由可由其他 Agent 复现。
