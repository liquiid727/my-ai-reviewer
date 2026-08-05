# PRD: 模拟面试创建与场景配置

**Status**: Approved for specification

**Prepared**: 2026-08-05

**Program**: `spec-draft/job-target-interview-program-2026-08-05.md`

**Sources**: `spec-draft/career-agent-product-direction-2026-08-04.md`, `spec-draft/career-agent-workflow-2026-08-05.md`

**Existing baseline**: AIP-001、RIP-003、RIP-007

## 1. Introduction / Overview

现有 AIP-001 的创建流程接收简历或 Builder 草稿、可选 `jd_text` 和题目数量，然后用户直接进入面试页面并开始生成问题。这条路径适合验证 MVP，但无法明确面试轮次、考察目标、时长、难度、风险覆盖和评分标准，也不能保证用户开始前知道本轮训练将考察什么。

本功能在“选择输入”和“开始会话”之间新增 Interview Plan。用户选择一个 Job Target、精确的 JD/Resume Version、场景、时长、难度和语言；系统生成一份结构化面试策略。用户审核阶段、能力覆盖、风险重点、题量和预计时长后明确批准，才能创建 Interview Session。

为保持模拟真实性，计划中的具体问题、expected signals 和 scoring rubric 不向用户展示。首版只支持文字面试；语音和其他复杂配置不出现在可用控件中。

## 2. Goals

- 将“创建面试方案”和“开始面试会话”拆成两个明确动作。
- 用版本化 Interview Scenario 表达面试类型，而不是依赖一段无法治理的 prompt。
- 让每份计划固定引用 Job Target、输入版本、匹配评估和场景版本。
- 在用户开始前展示阶段、覆盖能力、风险重点、题量和预计时长。
- 让内部问题、来源、预期信号和 rubric 可追踪但不提前泄露。
- 为后续 RAG、语音、题库和多轮训练保留清晰扩展位置，但不在首版启用。

## 3. User Stories

### US-001: 从目标岗位创建面试方案

**Description:** As a 用户, I want to 基于目标岗位和确定的输入版本创建方案 so that 本轮面试不会使用已经变更的简历或 JD。

**Acceptance Criteria:**

- [ ] 创建入口要求有效 `job_target_id`、`jd_version_id` 和 `resume_version_id`。
- [ ] 两个版本必须属于该 Job Target 可用上下文，且保持 ready/published 可读。
- [ ] 系统优先使用相同版本组合的最新 completed Match Assessment。
- [ ] 没有精确版本匹配评估时，系统先创建 assessment，并将方案显示为等待上游评估。
- [ ] 用户不能用可变 `jd_id`、复制的 `jd_text` 或未发布 Builder 内容绕过版本选择。
- [ ] 创建请求立即返回 Interview Plan ID 和生成状态，不等待完整 LLM 生成。
- [ ] 输入校验失败时返回可操作的上游修复入口。
- [ ] 后端集成测试覆盖有效输入、版本不属于工作区、assessment 等待和资源不存在。

### US-002: 选择首版面试配置

**Description:** As a 用户, I want to 选择少量关键配置 so that 我能控制训练目标而不被大量高级选项淹没。

**Acceptance Criteria:**

- [ ] 用户必须选择一个 Interview Scenario。
- [ ] 时长选项固定为 15、30、45 或 60 分钟。
- [ ] 难度选项固定为基础、标准或挑战。
- [ ] 语言选项固定为中文或英文，并默认使用当前界面语言。
- [ ] 首版 mode 固定为 `text`，页面不显示不可用的语音选项。
- [ ] 追问强度、即时提示、跳过权限和阶段进度使用场景默认值，不作为首版表单项。
- [ ] 重新打开表单时保留深链预选的 Job Target 和版本，不保留上次未提交的其他工作区配置。
- [ ] 中英文文案、typecheck、lint 和桌面/移动浏览器验收通过。

### US-003: 使用版本化面试场景

**Description:** As a 产品维护者, I want to 用结构化场景模板定义面试行为 so that 新增场景不需要复制整个 Agent 工作流。

**Acceptance Criteria:**

- [ ] 首版提供综合模拟、HR 初筛、技术一面、项目深挖、系统设计、行为面试和主管面试七个场景。
- [ ] 每个场景版本定义名称、用途、默认时长、默认难度、interviewer role/tone、阶段、competencies、follow-up policy 和 scoring dimensions。
- [ ] 阶段定义包含目标、时间预算和覆盖要求，不直接包含用户可编辑 prompt。
- [ ] 场景一经被 Interview Plan 引用即不可变；场景调整创建新版本。
- [ ] 已下线场景不能创建新计划，但历史计划和报告仍可读取其版本。
- [ ] 场景配置通过 schema 校验，阶段时长总和与默认总时长一致或在明示容差内。
- [ ] 首版不允许用户创建自定义场景模板。
- [ ] 单元测试覆盖七个模板的 schema、时长、能力维度和 follow-up 上限。

### US-004: 生成结构化 Interview Plan

**Description:** As a 用户, I want to 获得一份覆盖明确的面试策略 so that Agent 不会临场随机选择问题。

**Acceptance Criteria:**

- [ ] 方案生成输入固定为 selected versions、Match Assessment、Scenario Version 和用户配置。
- [ ] 方案包含预计时长、主问题数量、追问预算、阶段安排、重点能力、风险验证和 Coverage Matrix。
- [ ] 每个内部 planned question 包含 stage、competency、question、purpose、source evidence IDs、expected signals、follow-up candidates 和 scoring rubric。
- [ ] planned question 只能引用输入 Source Catalog 中存在的 resume/JD/match evidence IDs。
- [ ] 高重要性 JD 必备能力和 Match Assessment 高风险项必须进入 Coverage Matrix。
- [ ] 问题数量和阶段预算由时长与场景规则约束，LLM 不能突破配置上限。
- [ ] 方案生成失败时保存安全错误、retryable 标记和输入引用，不保存部分可执行计划。
- [ ] run ID/revision 阻止旧生成任务覆盖重新生成或拒绝后的计划。

### US-005: 审核策略而不提前看到题目

**Description:** As a 用户, I want to 审核本轮面试覆盖什么而不看到具体问题 so that 我能确认方向并保留模拟真实性。

**Acceptance Criteria:**

- [ ] review 页面展示场景、难度、语言、预计时长、阶段、题量、重点能力、风险验证和 JD 覆盖摘要。
- [ ] review 页面不返回或渲染 question text、expected signals、follow-up candidates 或 scoring rubric。
- [ ] 每个风险项显示其来源类别和安全摘要，但不暴露内部 prompt 或原始 LLM 响应。
- [ ] 页面显示 exact JD/Resume Version 和 Match Assessment 摘要。
- [ ] 输入已有更新版本时显示 stale 提示，但允许用户继续批准当前精确版本方案。
- [ ] 页面覆盖 generating、waiting_for_match、needs_review、failed、rejected 和 approved 状态。
- [ ] 失败状态提供重试，stale 状态提供“基于最新版本重新创建”操作。
- [ ] 使用可用的浏览器控制技能完成桌面和移动端验收。

### US-006: 批准、拒绝或重新生成方案

**Description:** As a 用户, I want to 对方案做明确决定 so that 系统不会在我确认前开始面试。

**Acceptance Criteria:**

- [ ] `needs_review` 方案提供批准、拒绝和重新生成三个命令。
- [ ] 批准请求携带 expected revision，并把完整内部计划快照固定为 approved。
- [ ] 并发 revision 冲突时要求刷新，不静默批准旧页面内容。
- [ ] 拒绝保存用户选择的可选原因，且不能再从该计划创建 Session。
- [ ] 重新生成创建新 run 并保留上一个计划记录用于审计；旧任务无权覆盖新结果。
- [ ] approved plan 不再修改；调整配置需要克隆配置并生成新计划。
- [ ] approved plan 最多创建一个非 cancelled Session。
- [ ] 后端测试覆盖批准幂等、冲突、拒绝、重新生成、stale worker 和重复 Session。

### US-007: 从现有资产进入统一创建流程

**Description:** As a 用户, I want to 从 JD、简历、匹配报告或 Job Target 进入同一方案创建页 so that 我不需要重复选择已经明确的输入。

**Acceptance Criteria:**

- [ ] JD 入口预选当前 ready JD Version 并取得/创建 Job Target。
- [ ] Resume 入口预选 Resume Version，并要求选择或创建 Job Target。
- [ ] Match Assessment 入口预选 Job Target、两个 versions 和 assessment。
- [ ] Job Target 入口默认使用其当前 JD Version 和默认 Resume Version。
- [ ] 用户可以在提交前切换到该工作区允许的其他 ready/published 版本。
- [ ] 非法或过期深链不会静默 fallback，而是显示缺失资源和恢复选项。
- [ ] 提交成功后进入 plan review，不直接跳到 Interview Session。
- [ ] 中英文文案、typecheck、lint 和浏览器验收通过。

## 4. Functional Requirements

- FR-1: 系统必须要求 Interview Plan 引用 Job Target。
- FR-2: 系统必须要求 Interview Plan 引用 JD Version 和 Resume Version。
- FR-3: 系统必须要求 Interview Plan 使用相同版本组合的 Match Assessment。
- FR-4: 系统必须在缺少 Match Assessment 时先创建评估。
- FR-5: 系统必须支持七个规定的首版 Interview Scenario。
- FR-6: 系统必须版本化 Interview Scenario。
- FR-7: 系统必须限制时长为 15、30、45 或 60 分钟。
- FR-8: 系统必须限制难度为基础、标准或挑战。
- FR-9: 系统必须限制语言为中文或英文。
- FR-10: 系统必须将首版 interview mode 固定为 text。
- FR-11: 系统必须异步生成 Interview Plan。
- FR-12: 系统必须为每次生成分配 run ID。
- FR-13: 系统必须用场景和时长约束阶段及问题预算。
- FR-14: 系统必须为 Interview Plan 创建 Coverage Matrix。
- FR-15: 系统必须覆盖高重要性 JD 要求和高风险匹配项。
- FR-16: 系统必须要求内部 planned question 引用允许的 evidence IDs。
- FR-17: 系统必须拒绝包含未知 evidence ID 的计划输出。
- FR-18: 系统必须向用户隐藏具体 planned questions。
- FR-19: 系统必须向用户隐藏 expected signals 和 scoring rubrics。
- FR-20: 系统必须在 plan review 展示策略、覆盖、风险、题量和时长。
- FR-21: 系统必须要求用户显式批准方案。
- FR-22: 系统必须使用 revision 保护批准与重新生成。
- FR-23: 系统必须将 approved plan 设为不可变。
- FR-24: 系统必须阻止 rejected 或 failed plan 创建 Session。
- FR-25: 系统必须限制 approved plan 最多创建一个非 cancelled Session。
- FR-26: 系统必须在输入存在更新版本时显示 stale 提示。
- FR-27: 系统必须保留历史计划的完整输入和场景版本引用。
- FR-28: 系统必须将 plan creation 与 session start 暴露为两个独立用户命令。

## 5. Non-Goals

- 不在首版支持语音、视频、ASR、TTS 或数字人。
- 不允许用户查看、增删改具体 planned questions 或 scoring rubric。
- 不允许用户创建自定义 Scenario。
- 不引入 Qdrant、题库 RAG、公司资料检索或网友面经。
- 不在本功能中执行问答、评估答案或生成最终报告。
- 不允许没有 JD Version 或 Resume Version 的通用面试。
- 不实现多面试官协作、审批流或共享模板市场。

## 6. Design Considerations

- 创建页使用清晰的版本选择器、场景选择控件、时长 segmented control、难度 segmented control 和语言选择器。
- 场景选项展示名称、用途和默认阶段摘要，不用营销式大卡片堆叠页面。
- review 页面突出“本轮会考察什么”，避免显示使用说明、prompt 或具体题目。
- 批准是主要命令，拒绝和重新生成是次级命令；覆盖操作必须有确认。
- loading 文案不能改变 plan summary 区域尺寸，避免生成中布局跳动。
- approved 状态提供“开始面试”命令；其他状态不显示可执行的 start 按钮。

## 7. Technical Considerations

- Interview Scenario 是稳定配置资源，不是前端常量和 prompt 字符串的重复集合。
- Interview Plan application use case 负责加载版本、取得 assessment、构建 Source Catalog、调用生成器和持久化完整结果。
- LLM provider-specific 行为留在现有 gateway/adapter，场景和计划领域不依赖 provider SDK。
- 外部 LLM 调用不持有数据库事务；finalize 使用 run/revision 条件写入。
- API 只返回 review 所需 projection；内部问题和 rubric 不进入普通前端 response type。
- 旧 `POST /interview/create` 在兼容期保留，但新 UI 必须走 plan-first 流程；弃用和移除由后续 SPEC/issue 管理。
- 所有 resume-derived Source Catalog 内容先通过 PrivacyGuard，日志只记录资源 ID、版本、run、模型和安全错误。

## 8. Success Metrics

- 100% 的新 UI 面试创建先产生 Interview Plan，再由用户批准后产生 Session。
- 100% 的 approved plans 固定记录 Job Target、JD Version、Resume Version、Match Assessment 和 Scenario Version。
- 高重要性 JD requirement 和高风险 match item 在 Coverage Matrix 中的计划覆盖率为 100%。
- review API 和浏览器状态中不出现 question text、expected signals 或 scoring rubric。
- 重试、拒绝、重新生成和并发批准均不会让 stale worker 覆盖用户最新决定。
- 所有后端、前端、浏览器、隐私和质量门禁通过。

## 9. Open Questions

当前无阻塞产品问题。正式 SPEC 阶段需要为七个场景确定精确阶段预算、题量映射、follow-up 上限和 scoring dimensions；这些值必须版本化并通过场景 fixture 验证。
