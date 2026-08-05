# PRD: 模拟面试运行与报告

**Status**: Approved for specification

**Prepared**: 2026-08-05

**Program**: `spec-draft/job-target-interview-program-2026-08-05.md`

**Sources**: `spec-draft/career-agent-product-direction-2026-08-04.md`, `spec-draft/career-agent-workflow-2026-08-05.md`

**Existing baseline**: AIP-001、RIP-008、RIP-009

## 1. Introduction / Overview

现有 AIP-001 已能运行文字问答、逐题评估、动态追问和异步报告，但会话直接从可变简历/JD 创建，状态只覆盖基础 pending/in-progress/completed/failed，前端在每题后立即展示评分，问题与回答也缺少独立的覆盖、事件、幂等和恢复合同。

本功能把运行时升级为由 approved Interview Plan 驱动的 Interview Session。系统按计划阶段和 Coverage Matrix 选择主问题，Evaluator 在后台评估回答并决定追问，但分数和改进反馈在面试结束前保持隐藏。会话支持暂停、恢复、跳过、主动结束、失败恢复和过期处理；题目、回答、评估和事件分别持久化，最终生成可追溯的岗位覆盖报告和后续行动建议。

首版仍为文字面试。它复用现有 LangGraph、LLM Gateway、Celery、PostgreSQL checkpointer、RIP-008 计划和 RIP-009 隐私能力，不创建微服务或真正的多 Agent 部署。

## 2. Goals

- 只允许 approved Interview Plan 创建和启动 Interview Session。
- 按阶段、时间预算、能力覆盖和风险优先级执行结构化文字面试。
- 将 Orchestrator、Interviewer、Evaluator、Context Retrieval 和 Report 职责分开。
- 让 Session 可暂停、恢复、重试、跳过、提前结束和安全过期。
- 使用独立问题、回答、评估和事件记录支持恢复、回放、评测和审计。
- 在面试中隐藏评分，在结束后提供证据支持的完整报告。
- 将用户选择的改进项显式加入现有 RIP-008 求职计划。

## 3. User Stories

### US-001: 从 approved plan 创建并开始 Session

**Description:** As a 用户, I want to 从我已批准的面试方案开始一场会话 so that 实际面试与我确认的策略一致。

**Acceptance Criteria:**

- [ ] Session 创建必须引用 approved Interview Plan，其他 plan 状态返回明确业务错误。
- [ ] Session 固定保存 plan snapshot、Scenario Version、JD Version、Resume Version 和 Match Assessment 引用。
- [ ] 同一 approved plan 最多存在一个非 cancelled Session；重复创建返回已有 Session。
- [ ] 创建与开始是两个命令；创建返回 `ready`，开始后才进入 `in_progress`。
- [ ] start 幂等：重复 start 不重复生成或插入第一题。
- [ ] 开始前再次对 masked resume/session context 执行 PrivacyGuard。
- [ ] 第一屏说明场景、预计时长和暂停/结束能力，不展示评分规则或完整问题列表。
- [ ] 后端集成测试和浏览器验收覆盖 ready、重复创建、重复 start、隐私拒绝和 plan 非 approved。

### US-002: 按计划和覆盖矩阵推进面试

**Description:** As a 用户, I want to 接受一场有阶段和重点的面试 so that 问题覆盖目标岗位而不是由模型随机发挥。

**Acceptance Criteria:**

- [ ] Orchestrator 根据当前阶段、剩余时间、Coverage Matrix、已问问题和追问预算选择下一步。
- [ ] 高重要性且尚未验证的 coverage item 优先于低重要性或已充分验证项。
- [ ] 主问题来自 approved plan；自适应追问必须关联原问题和触发 evaluation。
- [ ] 阶段至少支持 opening、resume/project verification、JD skill assessment、scenario/problem solving 和 candidate questions，具体组合由 Scenario Version 决定。
- [ ] 进入候选人反问阶段时允许 1 到 3 个问题；Interviewer 不得虚构公司内部信息。
- [ ] 时间预算不足时按场景政策结束低优先级 coverage，而不是无限追加问题。
- [ ] 每次状态转换持久化后才把下一问题返回浏览器。
- [ ] 确定性 Orchestrator 测试覆盖优先级、时间不足、coverage 完成和候选人反问分支。

### US-003: 提交回答并进行隐藏评估

**Description:** As a 用户, I want to 专注回答而不被即时分数打断 so that 训练更接近真实面试。

**Acceptance Criteria:**

- [ ] 回答提交要求当前 question ID、非空文本和 client idempotency key。
- [ ] 重复 idempotency key 返回已有处理结果，不创建第二条回答或重复 LLM 调用。
- [ ] 回答在进入外部 LLM 前执行本地直接标识符处理；持久化和 LLM 输入使用 masked answer text。
- [ ] Evaluator 独立输出 correctness、depth、evidence、structure、communication、key signals、missing signals、needs_followup 和 confidence。
- [ ] Evaluator 只能使用当前问题 rubric、允许的 session context 和该题历史回答。
- [ ] evaluation schema 非法或含未知 evidence ID 时内部重试；仍失败则保留可恢复失败状态。
- [ ] 回答成功后 UI 只显示已提交状态和下一问题/追问，不显示 score、feedback、hit 或 missed points。
- [ ] 测试覆盖正常回答、过短回答、重复提交、隐私拒绝、evaluation 失败和隐藏字段 response contract。

### US-004: 生成受约束的动态追问

**Description:** As a 用户, I want to 在回答模糊或证据不足时接受相关追问 so that 系统能验证技术深度和项目真实性。

**Acceptance Criteria:**

- [ ] 追问只在 evaluation 命中 Scenario follow-up policy 时生成。
- [ ] 追问必须说明其关联的原 question、coverage item 和触发原因。
- [ ] 单题追问深度不能超过 Scenario Version 的 `max_depth`。
- [ ] 达到最大深度、coverage evidence 已充分或剩余时间不足时强制进入下一主问题或结束阶段。
- [ ] 追问不能复述原问题，不能引入 Resume/JD/Match Source Catalog 之外的候选人事实。
- [ ] 追问与主问题使用相同 answer endpoint 和 idempotency contract。
- [ ] 追问状态单独记录为 planned、asked、answered、evaluated 或 abandoned。
- [ ] 单元与集成测试覆盖 vague answer、missing evidence、maximum depth 和 no-time-left 分支。

### US-005: 暂停、恢复和处理并发

**Description:** As a 用户, I want to 暂停后从同一位置继续 so that 页面关闭或短暂中断不会丢失面试进度。

**Acceptance Criteria:**

- [ ] `in_progress` Session 可以暂停为 `paused`，并记录最后活动时间和当前问题。
- [ ] `paused` Session 可以恢复为 `in_progress`，恢复后不重复已经 asked 的问题。
- [ ] pause、resume 和 answer 命令携带 expected revision；冲突时返回 reload/reconcile 响应。
- [ ] 页面刷新后从持久化 Session projection 和 LangGraph checkpoint 恢复消息、阶段、进度和当前问题。
- [ ] 页面失去所有权后停止轮询或请求；恢复时重新获取服务端状态。
- [ ] 同时两个标签页提交时只允许一个 revision 成功，失败标签页不覆盖成功回答。
- [ ] checkpointer 不作为唯一业务状态源；PostgreSQL Session/Question/Event 记录可重建用户可见状态。
- [ ] 使用两个独立数据库会话测试并发 answer/pause 竞争。

### US-006: 跳过、主动结束、失败和过期

**Description:** As a 用户, I want to 在无法继续时安全结束或恢复 so that Session 不会永久卡在进行中。

**Acceptance Criteria:**

- [ ] 当前 Scenario 允许时，用户可以跳过问题；跳过记录原因并更新 coverage 为未验证。
- [ ] Session 开始前取消进入 `cancelled`，不生成报告。
- [ ] Session 开始后主动结束进入 `terminated`，并异步生成标记为 incomplete 的部分报告。
- [ ] 正常覆盖完成进入 `completing`，报告成功后进入 `completed`。
- [ ] 可重试依赖失败保存安全错误、失败步骤和 retryable 标记，并提供恢复命令。
- [ ] 超过 policy TTL 的 ready/paused Session 进入 `expired`，不能再接受回答。
- [ ] stale worker 或旧 revision 不能把 cancelled、terminated、expired 或 completed Session 改回进行中。
- [ ] 集成测试覆盖 skip、cancel、terminate、report failure、retry、expiry 和 stale worker。

### US-007: 保存独立问题、回答、评估和事件

**Description:** As a 产品维护者, I want to 拥有结构化运行记录 so that 我能恢复会话、分析覆盖率并建立 Agent Eval。

**Acceptance Criteria:**

- [ ] 问题记录保存 plan question、实际文本、stage、competency、purpose、source IDs、顺序和状态。
- [ ] 问题状态支持 `planned`、`asked`、`answered`、`evaluated`、`followed_up`、`skipped` 和 `abandoned`。
- [ ] 回答记录与 evaluation 分离，evaluation 记录 evaluator/prompt/model/policy version 和安全结构化结果。
- [ ] Session event 使用单调 sequence，至少记录 created、started、question.asked、answer.submitted、answer.evaluated、followup.generated、paused、resumed、completed 和 report.generated。
- [ ] 同一 Session 的 event sequence 唯一，命令事务同时写业务状态和对应 event。
- [ ] event payload 只保存允许字段，不保存 prompt、completion、API key、原始未屏蔽简历或 answer。
- [ ] 可以从关系数据和 events 生成只读 session timeline 和 coverage projection。
- [ ] 数据库和集成测试覆盖事件顺序、事务回滚和 projection 重建。

### US-008: 生成证据支持的面试报告

**Description:** As a 用户, I want to 在面试结束后查看完整报告 so that 我能理解岗位适配、强项、弱项和下一步训练重点。

**Acceptance Criteria:**

- [ ] 报告包含总体表现、场景、输入版本、完成度和是否为 incomplete。
- [ ] 报告维度至少覆盖技术正确性、技术深度、项目真实性、问题分析、方案权衡、表达结构和岗位适配度。
- [ ] 高表现问题展示问题摘要、回答摘要、优秀点和对应能力证据。
- [ ] 薄弱问题展示回答缺口、不足原因、推荐答题结构和练习建议。
- [ ] JD coverage 展示已验证、表现良好、基本满足、存在风险和尚未验证的 requirement 数量。
- [ ] 报告结论聚合单题 evaluations 和 Coverage Matrix，不允许 LLM 无证据重新发明分数。
- [ ] report generation 失败时 Session 保持 `completing` 或进入可重试失败状态，问答数据不丢失。
- [ ] 报告生成完成前不向用户返回任何单题 score 或 feedback。
- [ ] 中英文文案、typecheck、lint 和桌面/移动浏览器验收通过。

### US-009: 将建议显式加入求职计划

**Description:** As a 用户, I want to 选择报告中的建议加入现有求职计划 so that 面试结果能转化为可执行任务而不擅自修改我的计划。

**Acceptance Criteria:**

- [ ] 报告建议包含稳定 recommendation ID、类别、标题、行动说明、优先级、证据和目标 JD requirement。
- [ ] 用户可以多选建议并选择当前 Job Target 下的 RIP-008 plan。
- [ ] 应用前展示将新增的任务和目标 plan，不自动提交。
- [ ] 提交使用 RIP-008 manual task contract 和 expected revision，不直接写计划表。
- [ ] revision 冲突时保留用户选择并要求刷新，不重复创建已经成功应用的 recommendation。
- [ ] 成功后 recommendation 标记 applied plan/task IDs，但报告正文保持不可变。
- [ ] 本功能不自动修改 Candidate Profile、Resume Version 或 Job Target 状态。
- [ ] 集成和浏览器测试覆盖选择、取消、成功、部分失败、冲突和重复应用。

### US-010: 查看会话历史和恢复入口

**Description:** As a 用户, I want to 从 Job Target 或面试列表查看历史会话 so that 我能继续未完成训练并对比已完成报告。

**Acceptance Criteria:**

- [ ] 列表展示目标岗位、场景、版本、状态、进度、开始时间和报告分数摘要。
- [ ] ready/paused/retryable Session 显示继续入口，completed/terminated 显示报告入口。
- [ ] cancelled/expired/failed 状态显示原因类别和可用的重新创建或 retry 命令。
- [ ] 列表支持 Job Target、场景和状态筛选，并默认按最近活动时间倒序。
- [ ] 历史详情可查看只读 timeline、问题状态和最终报告，但不显示内部 prompt/rubric。
- [ ] 页面覆盖 loading、empty、failure、mutation pending、conflict 和 expired 状态。
- [ ] 深链刷新后仍恢复到正确 Session，不以最新 Session 替代指定 ID。
- [ ] 使用可用的浏览器控制技能完成桌面和移动端验收。

## 4. Functional Requirements

- FR-1: 系统必须只允许 approved Interview Plan 创建 Session。
- FR-2: 系统必须固定保存 Session 的 plan 和输入版本引用。
- FR-3: 系统必须限制 approved plan 最多一个非 cancelled Session。
- FR-4: 系统必须将 Session 创建和开始作为两个命令。
- FR-5: 系统必须使 Session start 幂等。
- FR-6: 系统必须按 Scenario stages 和 Coverage Matrix 编排面试。
- FR-7: 系统必须按 importance 和 evidence sufficiency 选择下一 coverage item。
- FR-8: 系统必须用时间和追问预算限制运行。
- FR-9: 系统必须允许候选人在规定阶段提出 1 到 3 个问题。
- FR-10: 系统必须阻止 Interviewer 虚构公司内部信息。
- FR-11: 系统必须要求 answer 提交包含 idempotency key。
- FR-12: 系统必须在外部 LLM 前处理 answer 中的直接标识符。
- FR-13: 系统必须将 masked answer text 作为持久化和 LLM 输入。
- FR-14: 系统必须将 Evaluator 与 Interviewer 逻辑分离。
- FR-15: 系统必须隐藏会话中的 score 和 feedback。
- FR-16: 系统必须按 Scenario follow-up policy 生成追问。
- FR-17: 系统必须限制单题追问深度。
- FR-18: 系统必须支持 pause 和 resume。
- FR-19: 系统必须使用 revision 保护 answer、pause 和 resume。
- FR-20: 系统必须支持 Scenario 允许的 question skip。
- FR-21: 系统必须支持 start 前 cancel。
- FR-22: 系统必须支持 start 后 terminate 并生成 incomplete report。
- FR-23: 系统必须使 expired Session 拒绝新回答。
- FR-24: 系统必须拒绝 stale worker 改写终态。
- FR-25: 系统必须分别持久化 question、answer、evaluation 和 event。
- FR-26: 系统必须为 Session events 分配单调 sequence。
- FR-27: 系统必须在状态事务中写入对应 event。
- FR-28: 系统必须从关系状态而非仅 checkpointer 恢复用户 projection。
- FR-29: 系统必须异步生成完整或 incomplete report。
- FR-30: 系统必须从 evaluations 和 Coverage Matrix 聚合报告。
- FR-31: 系统必须在报告中展示 JD coverage。
- FR-32: 系统必须允许用户显式选择建议加入 RIP-008 plan。
- FR-33: 系统必须使用 RIP-008 revision contract 创建后续任务。
- FR-34: 系统必须阻止同一 recommendation 重复应用。
- FR-35: 系统必须提供 Session 列表、筛选、恢复和报告入口。
- FR-36: 系统必须在日志、事件和错误中排除敏感内容。

## 5. Non-Goals

- 不支持语音、视频、ASR、TTS、摄像头、表情或语速评分。
- 不支持代码执行、在线 IDE、Sandbox 或系统设计白板。
- 不启用 Qdrant、公共题库 RAG、公司资料检索或联网面试信息。
- 不在会话中向用户展示即时评分、标准答案或改进提示。
- 不把 Orchestrator、Interviewer、Evaluator 或 Report 部署为独立服务或自由协作的 Multi-Agent。
- 不自动更新 Candidate Profile、Career Evidence Graph 或长期能力等级。
- 不自动创建、删除或完成 RIP-008 任务。
- 不实现实时 WebSocket 推送；首版继续使用 HTTP command/query 和必要轮询。

## 6. Design Considerations

- 面试页面保持稳定的题目区、回答区、阶段/进度和控制栏，不在每题后插入评分卡造成节奏中断。
- 暂停、结束和跳过使用明确图标/命令；结束和取消需要确认。
- 当前问题、回答 pending 状态和连接失败不能改变输入区固定尺寸或覆盖前文。
- 报告页优先展示岗位覆盖和证据，再展示视觉化总分；图表必须有文本替代。
- 历史列表保持高信息密度，可快速识别继续训练、等待报告、已完成和不可恢复状态。
- 所有错误映射为本地化、可恢复的用户文案，不直接渲染后端对象。

## 7. Technical Considerations

- LangGraph 负责流程编排和 checkpoint；application use case 负责业务事务、revision、idempotency、事件和终态。
- 一个工作流内部使用不同节点和 prompt，不建立网络化 Multi-Agent 架构。
- Session、Question、Answer、Evaluation、Event 和 Report 的数据模型在正式 SPEC 中明确迁移与 AIP-001 兼容策略。
- Celery report task 使用统一 PID-owned async runner、run ownership、超时、有限重试和安全错误。
- LLM 调用全部通过现有 gateway，采用 Pydantic v2 structured output、明确 timeout 和 PrivacyGuard。
- event/outcome projection 查询避免逐 Session/Question N+1；列表不加载完整 transcript 或 report。
- 旧 `/interview/create` 和当前即时反馈 response 需要兼容期；新 UI 不依赖被弃用字段，移除由独立 issue 管理。

## 8. Success Metrics

- 100% 的新 Session 来源于 approved Interview Plan，并固定记录全部输入版本。
- Session 在刷新、暂停和 worker 重启后能从持久化状态恢复到同一当前问题。
- 重复 answer idempotency key 和并发标签页不会产生重复回答或重复 evaluation。
- 高重要性 coverage item 的已验证/未验证状态在报告中可与问题和 evidence 对应。
- 会话期间的所有 API response 和浏览器状态均不包含 score、feedback 或 rubric。
- completed/terminated 报告中的每个优势、风险和建议都有 evidence 或明确的 insufficient-evidence 标记。
- 用户可在报告中显式选择建议并无重复地加入 RIP-008 plan。
- 后端、集成、迁移、前端、浏览器、隐私和质量门禁全部通过。

## 9. Open Questions

当前无阻塞产品问题。正式 SPEC 阶段需要确定 Session TTL、每个 Scenario 的 skip policy、事件 payload allow-list、terminated report 的最低回答数量和旧 AIP-001 transcript 的迁移方式；这些值必须形成稳定配置并覆盖边界测试。
