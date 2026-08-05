# PRD: 简历与 JD 匹配评估

**Status**: Approved for specification

**Prepared**: 2026-08-05

**Program**: `spec-draft/job-target-interview-program-2026-08-05.md`

**Sources**: `spec-draft/career-agent-product-direction-2026-08-04.md`, `spec-draft/career-agent-workflow-2026-08-05.md`

**Existing baseline**: RIP-002、RIP-003、RIP-007、RIP-008

## 1. Introduction / Overview

现有 RIP-003 可以把 Candidate Profile 与 JD 的必备技能做确定性匹配，并持久化总分、缺失技能、风险和建议。但当前算法主要覆盖技能名称，输入只引用可变的 `resume_id` 和 `jd_id`，缺少版本固定、多维评分、证据质量判断和完整的匹配报告页面。

本功能把匹配升级为可重放的 Match Assessment。用户明确选择一个不可变 Resume Version 和一个不可变 JD Version；系统根据版本化评分策略计算总分、维度分、证据、缺口类别和下一步建议。报告用于帮助用户判断如何优化材料和准备面试，但不会因为低分阻止训练。

首次执行匹配或其他下游动作时，系统为该 JD 身份幂等创建最小 Job Target。Job Target 只负责归组相关版本和结果，不在本功能中实现投递阶段、提醒或完整职业记忆。

## 2. Goals

- 固定匹配输入版本，使历史评分和解释不随 JD 或简历编辑发生含义漂移。
- 建立最小 Job Target，串联同一目标岗位下的匹配、计划和面试资产。
- 将技能匹配扩展为八个可解释维度和版本化评分政策。
- 明确区分真实能力缺口、简历表达缺口、证据缺口和硬性条件风险。
- 让每项匹配结论能够回到具体 JD evidence 和候选人 evidence。
- 提供从 JD、简历和独立匹配中心进入的统一用户流程。
- 为 Interview Plan 和 RIP-008 求职计划提供稳定的 assessment 输入。

## 3. User Stories

### US-001: 创建或复用目标岗位工作区

**Description:** As a 用户, I want to 在第一次针对某个 JD 行动时获得一个目标岗位工作区 so that 后续匹配、计划和面试记录集中在同一上下文。

**Acceptance Criteria:**

- [ ] 从 JD 匹配、面试方案或求职计划入口触发时，系统按当前匿名用户域和 JD 身份幂等取得或创建 active Job Target。
- [ ] 仅导入、审核、发布或浏览 JD 不创建 Job Target。
- [ ] 同一 JD 身份在匿名用户域内同时最多存在一个 active Job Target。
- [ ] Job Target 至少展示岗位、公司、当前选定 JD Version、默认 Resume Version 和最近活动时间。
- [ ] 用户可以更换默认 Resume Version；该操作不修改已有 Match Assessment。
- [ ] 用户可以归档 Job Target；归档不删除下游历史资源。
- [ ] 并发 get-or-create 不产生重复 active Job Target。
- [ ] 后端集成测试和浏览器验收覆盖首次创建、复用、切换版本和归档。

### US-002: 发布并选择不可变 Resume Version

**Description:** As a 用户, I want to 选择一个确定的简历版本 so that 匹配报告能准确说明当时使用了哪些候选人事实。

**Acceptance Criteria:**

- [ ] 可选输入包括已完成解析的简历和已保存的 Builder 草稿 revision。
- [ ] 首次将某个解析结果或 Builder revision 用于下游时，系统创建不可变 Resume Version。
- [ ] Resume Version 保存来源 resume/draft ID、来源 revision、content hash、masked content/profile snapshot、privacy policy version 和发布时间。
- [ ] Resume Version 不保存可恢复的真实姓名、邮箱、电话、地址或任意未声明的 PII。
- [ ] 已发布 Resume Version 不可修改；简历或 Builder 内容变化后必须发布新版本。
- [ ] 版本选择器显示名称、来源、发布时间和当前/历史标记。
- [ ] PrivacyGuard 拒绝的版本不能进入匹配，不能降级为发送未屏蔽内容。
- [ ] 测试证明旧 Resume Version 在 Builder 保存新 revision 后保持不变。

### US-003: 选择版本并创建 Match Assessment

**Description:** As a 用户, I want to 选择一份简历版本和一个 JD 版本发起评估 so that 报告对应明确的输入组合。

**Acceptance Criteria:**

- [ ] JD 详情、简历详情和独立匹配中心最终使用同一创建流程。
- [ ] 创建前必须选择一个 ready JD Version 和一个可用 Resume Version。
- [ ] 请求创建后立即返回 Match Assessment ID 和非终态，不等待完整 LLM 判断。
- [ ] 评估状态至少包含 `queued`、`evaluating`、`completed` 和 `failed`。
- [ ] Assessment 保存 Job Target、两个 version ID、scoring policy version、run ID、模型信息和创建时间。
- [ ] 相同输入版本和评分政策的 completed assessment 默认复用；用户可显式要求重新评估。
- [ ] stale worker 不能覆盖由重新评估产生的新 run。
- [ ] 页面覆盖 loading、empty、queued、evaluating、completed、failed、timeout 和 retry 状态。

### US-004: 使用版本化多维评分政策

**Description:** As a 用户, I want to 看见总分由哪些维度构成 so that 我不会被一个无法解释的百分比误导。

**Acceptance Criteria:**

- [ ] 评分政策包含必备技能 25、经验年限 15、项目经历 20、岗位职责 15、技术栈与工具 10、行业/业务 5、基础条件 5、优先项 5，共 100 分。
- [ ] 缺失核心必备技能时总分最高为 75。
- [ ] 工作年限达到政策定义的严重不足条件时总分最高为 70。
- [ ] 同时触发多个封顶规则时使用最低上限。
- [ ] 明确学历要求不满足时记录硬性条件风险；首版不默认设置额外总分上限。
- [ ] 每项分数保存原始得分、加权得分、适用规则和封顶前后总分。
- [ ] 所有阈值、别名和封顶规则归属于 immutable scoring policy version。
- [ ] 固定输入和固定 policy 的纯评分测试每次产生相同结果。

### US-005: 生成证据支持的匹配判断

**Description:** As a 用户, I want to 知道每项 JD 要求由哪些简历事实支持 so that 我能区分会做、写得不好和完全没有证据。

**Acceptance Criteria:**

- [ ] 技能名称先经过版本化别名词典归一化，例如 Go/Golang、Postgres/PostgreSQL。
- [ ] 硬性字段通过确定性规则评估，不允许 LLM 改写明确的年限、学历、地点或证书事实。
- [ ] 项目和职责相关性通过受约束的结构化 LLM 输出判断，并要求返回允许的 evidence IDs。
- [ ] 未知 evidence ID、无对应来源的断言或 schema 不合法会使评估失败或内部重试，不能作为成功结果落库。
- [ ] 候选人 evidence 只来自所选 Resume Version，JD evidence 只来自所选 JD Version。
- [ ] 首版不启用 Qdrant 或 Embedding 相似度；后续只有在评测集证明收益后再增加该评分步骤。
- [ ] 评估快照不包含 identity PII、原始未屏蔽简历或 provider 原始响应。
- [ ] 单元测试覆盖别名、硬规则、evidence allow-list、恶意输入和无证据场景。

### US-006: 区分四类缺口和风险

**Description:** As a 用户, I want to 看见缺口属于能力、表达、证据还是硬性条件 so that 我能采取正确行动。

**Acceptance Criteria:**

- [ ] `capability_gap` 表示已有证据显示能力未达到 JD 要求。
- [ ] `expression_gap` 表示相关事实存在，但当前简历表述未清楚对应 JD 要求。
- [ ] `evidence_gap` 表示系统没有足够证据判断用户是否具备该能力。
- [ ] `hard_constraint_risk` 表示年限、学历、地点、证书等明确条件存在风险。
- [ ] evidence 不足时文案使用“未找到可证明内容”，不得断言用户不会该技能。
- [ ] 每项缺口包含严重度、JD requirement evidence、candidate evidence 或 missing-evidence 标记、置信度和建议动作类型。
- [ ] 同一 requirement 不会以冲突类别重复出现；无法确定时优先归为 evidence gap。
- [ ] 合成测试覆盖“会但没写”“写了但无具体证据”“明确不会”“硬条件不满足”四类场景。

### US-007: 查看完整匹配报告

**Description:** As a 用户, I want to 在一个页面理解匹配结论、证据和下一步 so that 我能决定如何准备，而不是只看到一个分数。

**Acceptance Criteria:**

- [ ] 报告顶部显示综合分、建议结论、输入版本和评分政策版本。
- [ ] 报告展示八个维度的得分和适用的封顶规则。
- [ ] 已匹配能力逐项展示 JD 要求、候选人证据、判断和置信度。
- [ ] 能力缺口按四类组织，并允许跳转到对应 evidence 摘要。
- [ ] 报告明确展示“建议训练状态”：`ready`、`ready_with_risks` 或 `build_evidence_first`。
- [ ] 建议训练状态只提供建议，任何 completed assessment 都允许继续创建模拟面试方案。
- [ ] 报告页面覆盖 loading、failure、retry 和版本已非当前的 stale 提示。
- [ ] 中英文文案、前端 typecheck、lint 和桌面/移动浏览器验收通过。

### US-008: 从评估进入下一步行动

**Description:** As a 用户, I want to 从报告直接进入简历优化、面试准备或求职计划 so that 匹配结果能转化为行动。

**Acceptance Criteria:**

- [ ] “优化当前简历”传递 Resume Version 来源和匹配证据，不直接改写已发布版本。
- [ ] “生成针对性简历”创建新的 Builder 工作副本，不覆盖当前 Resume Version。
- [ ] “创建模拟面试方案”传递 Job Target ID 和 Match Assessment ID。
- [ ] “加入求职计划”使用现有 RIP-008 创建/打开流程，并传递精确 version/assessment 上下文。
- [ ] 下游页面发现输入版本不可用时显示恢复路径，不静默切换到最新版本。
- [ ] 更新 JD 或简历后页面提示创建新的 assessment，不自动覆盖当前报告。
- [ ] 深链刷新后仍保持选中的版本和 assessment。
- [ ] 使用可用的浏览器控制技能验证所有入口及无效输入分支。

## 4. Functional Requirements

- FR-1: 系统必须在首次下游动作时幂等创建 Job Target。
- FR-2: 系统必须限制同一匿名用户域和 JD 身份最多一个 active Job Target。
- FR-3: 系统必须允许归档 Job Target。
- FR-4: 系统必须将解析简历或 Builder revision 发布为不可变 Resume Version。
- FR-5: 系统必须在 Resume Version 中保存来源 revision 和 content hash。
- FR-6: 系统必须在 Resume Version 中只保存 masked snapshot。
- FR-7: 系统必须要求 Match Assessment 引用 JD Version 和 Resume Version。
- FR-8: 系统必须为 Match Assessment 分配 run ID。
- FR-9: 系统必须异步执行包含 LLM 判断的 Match Assessment。
- FR-10: 系统必须复用相同输入和政策的 completed assessment。
- FR-11: 系统必须允许用户显式重新评估。
- FR-12: 系统必须按八个规定维度计算评分。
- FR-13: 系统必须使用 25/15/20/15/10/5/5/5 权重。
- FR-14: 系统必须对缺失核心技能应用 75 分上限。
- FR-15: 系统必须对严重年限不足应用 70 分上限。
- FR-16: 系统必须版本化评分政策、阈值和技能别名。
- FR-17: 系统必须使用确定性规则评估明确硬条件。
- FR-18: 系统必须约束 LLM 只能引用输入 Source Catalog 的 evidence IDs。
- FR-19: 系统必须拒绝包含未知 evidence ID 的 LLM 结果。
- FR-20: 系统必须输出 capability、expression、evidence 和 hard-constraint 四类缺口。
- FR-21: 系统必须将 evidence 不足描述为未知而不是能力缺失。
- FR-22: 系统必须持久化维度分、规则、证据、置信度和封顶过程。
- FR-23: 系统必须提供完整匹配报告和输入版本信息。
- FR-24: 系统必须允许任意 completed assessment 进入模拟面试方案创建。
- FR-25: 系统必须在输入更新后提示 assessment stale。
- FR-26: 系统必须阻止下游静默替换输入版本。
- FR-27: 系统必须为报告提供简历优化、面试方案和求职计划入口。
- FR-28: 系统必须在 LLM 前对 Resume Version snapshot 执行 PrivacyGuard。

## 5. Non-Goals

- 不在首版启用 Embedding、Qdrant、Hybrid Search 或 Rerank。
- 不构建通用技能知识图谱或全岗位能力模型平台。
- 不根据低匹配分禁止用户投递或进行模拟面试。
- 不自动修改 Candidate Profile、Resume Version 或 JD Version。
- 不自动生成课程内容或执行求职计划任务。
- 不实现真实招聘决策或向企业输出录用建议。
- 不实现多用户共享、权限或租户隔离。

## 6. Design Considerations

- 三个入口汇聚到同一版本选择和评估页面，避免维护三套匹配逻辑。
- 版本选择使用可扫描的选择器，明确显示当前版本、历史版本和发布时间。
- 匹配报告保持工作型信息密度，优先呈现证据和缺口，不使用只强调总分的营销式布局。
- 维度适合使用雷达图或条形比较，但必须同时提供可访问的文本数值和解释。
- 所有建议按钮保留明确命令含义；不会因为图标或颜色暗示系统已经自动执行动作。
- stale 提示允许查看旧报告和创建新评估，不强制跳转。

## 7. Technical Considerations

- 正式 SPEC 定义 Job Target、Resume Version、Match Assessment 和 scoring policy 的稳定数据合同及迁移顺序。
- 现有 `jd_match_results` 需要兼容迁移或明确只读保留，不能让新旧结果在同一接口中语义不明。
- 评分聚合与封顶规则属于纯 domain policy；数据库、LLM 和 HTTP 不进入该计算模块。
- Source Catalog builder 负责去敏、ID 稳定性和 evidence allow-list；LLM 只返回结构化判断。
- Match orchestration 位于 application 层；API 只创建/查询资源，Celery task 只作为进程边界。
- 前端通过 `frontend/src/api/` 和 `frontend/src/types/` 维护 version 与 assessment contract。
- API 保持 `/api/v1` 和 `APIResponse`；旧 `/jd/match` 的兼容/弃用策略在 SPEC 中明确。

## 8. Success Metrics

- 100% 的新 Match Assessment 同时记录 `job_target_id`、`resume_version_id`、`jd_version_id` 和 scoring policy version。
- 固定输入、固定政策在回归测试中产生确定的规则分和封顶结果。
- 每个 completed assessment 的 requirement 判断都包含有效 evidence ID 或明确的 missing-evidence 状态。
- 发布新 JD/Resume Version 后，旧 assessment 的输入、分数和报告完全不变。
- 用户可以在报告两次操作内进入简历优化、Interview Plan 或 RIP-008 计划流程。
- 迁移、后端、前端、浏览器和隐私门禁全部通过。

## 9. Open Questions

当前无阻塞产品问题。正式 SPEC 需要定义“严重年限不足”的精确政策阈值、旧 `jd_match_results` 的迁移方式，以及相同输入重新评估的保留数量；这些决定必须版本化且有测试 fixture。
