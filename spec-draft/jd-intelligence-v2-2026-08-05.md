# PRD: JD Intelligence v2

**Status:** Accepted for technical specification

**Requested at:** 2026-08-05

**Operating mode:** GoalSpec

**Baseline:** RIP-002, RIP-003, RIP-007, RIP-008, RIP-009

## 1. Introduction

当前系统已经支持 JD 文本、PDF、DOCX、TXT、Markdown 和公开 URL 导入，并使用 LLM 把正文抽取为岗位、公司、地点、职级、职责及技能字段。当前 JD 与简历匹配则是 `rules_v1`：只比较 Candidate Profile 中的技能和能力标签，按关键/非关键技能计算单一分数。

本增量补齐三类缺口：

1. 用户可上传一张或多张 JD 图片，由已配置且明确支持 Vision 的 LLM 读取图片文字，再复用现有 JD 结构化、去重、编辑和状态链路。
2. 匹配升级为“确定性硬条件 + 有证据约束的 LLM 多维分析”，同时保留现有规则匹配兼容接口。
3. 匹配结果具备输入快照、模型/Prompt/算法版本和 freshness，前端、求职计划及面试链路不会把旧结果误当作最新结论。

这不是让 LLM 独立作出录用决定。系统提供筛选辅助、差距解释和证据定位；硬条件失败和最终处置均需人工确认。

## 2. Current Baseline and Drift

- 已实现：`/jd/import/text|file|url`、JD Library、异步处理、LLM 文本结构化抽取、人工编辑、重复检测、`POST /jd/match` 规则匹配及结果落库。
- 当前图片并非受支持的 JD 来源；扫描 PDF 也只会尝试提取文本层，没有 Vision 回退。
- 当前 LLM gateway 没有明确的多模态能力契约；不能根据 provider 或模型名称猜测 Vision 能力。
- 当前匹配不读取职责、工作经历、项目、教育或事实证据，不执行真正的硬条件筛选，也没有模型/Prompt/输入版本。
- RIP-003、RIP-007、RIP-008 的状态文字与代码存在漂移。代码存在不等于已经通过迁移、集成和浏览器验收；本增量必须先记录 as-built 基线，再实现新增能力。

## 3. Goals

- 支持 PNG、JPEG/JPG、WEBP 的单图和多图 JD 导入，并异步获得可编辑的结构化 JD。
- Vision LLM 调用只在配置明确声明并验证对应能力后发生。
- 图片转写与 JD 结构化分成两个可追溯阶段，保留页序、模型版本和安全错误信息。
- 使用 JD 结构和已脱敏的 Resume Facts/Profile 进行多维匹配，每个结论必须引用输入证据。
- 将显式硬条件的 `pass/fail/unknown` 与软评分分离；`unknown` 不得自动等同于失败。
- 版本化保存匹配结果，并在 JD、简历事实、匹配算法、Prompt 或模型变更时正确标记 stale。
- 在 JD 详情页展示硬条件、维度分数、证据、置信度、风险和重新计算状态。
- 修复 PRD、SPEC、issue、实现与测试之间的可追溯漂移。

## 4. User Stories

### US-001: 上传图片 JD

**Description:** 作为招聘人员，我希望上传一张或多张 JD 截图，以便无需手工转录职位描述。

**Acceptance Criteria:**
- [ ] 支持 PNG、JPG/JPEG、WEBP，最多 8 张。
- [ ] 单张不超过 10MB，总大小不超过 30MB；损坏文件、伪造 MIME、超像素图片在入队前被拒绝。
- [ ] 上传成功立即返回 processing JD，不同步等待 LLM。
- [ ] 原有文本、文件和 URL 导入行为不回归。
- [ ] 在浏览器验证正常、超限、损坏、失败与重试状态。

### US-002: 使用 Vision LLM 转写图片文字

**Description:** 作为招聘人员，我希望系统调用已配置的 Vision LLM 读取图片文字，以便复杂截图仍可进入 JD 识别链路。

**Acceptance Criteria:**
- [ ] 仅 `supports_vision=true` 且配置已验证时发送图片。
- [ ] provider-specific 图片消息只存在于 infrastructure adapter。
- [ ] 转写结果按图片顺序形成文本块，并记录模型、转写版本和警告。
- [ ] Vision 超时、限流、非法输出和无可读文字均进入稳定失败状态。
- [ ] 日志、错误响应和任务元数据不包含图片 base64 或完整转写正文。

### US-003: 复用 JD 结构化和人工修正

**Description:** 作为招聘人员，我希望图片转写后沿用现有 JD 抽取与编辑体验，以便所有来源具有一致的数据结构。

**Acceptance Criteria:**
- [ ] 图片转写文本进入现有规范化、重复检测和 `JDExtractor`。
- [ ] ready 结果包含 title、company、location、seniority、responsibilities、required/preferred skills 及 evidence。
- [ ] Vision 转写和文本结构化任一阶段失败时不得产生 ready 半成品。
- [ ] 人工修改字段继续受 `field_sources` 和乐观并发控制保护。

### US-004: 明确 LLM 能力配置

**Description:** 作为系统管理员，我希望知道当前 LLM 是否支持文本结构化和图片理解，以便在执行前发现不兼容配置。

**Acceptance Criteria:**
- [ ] 配置保存 `supports_vision`、结构化输出支持、图片数量和大小能力。
- [ ] 能力由显式配置或验证结果产生，不根据模型名隐式猜测。
- [ ] 自定义/OpenAI-compatible endpoint 未声明 Vision 时拒绝图片任务。
- [ ] 设置页显示能力及最近验证状态。

### US-005: 执行可解释的硬条件筛选

**Description:** 作为招聘人员，我希望先查看岗位明确硬条件是否满足，以便区分“不满足”与“简历没有提供信息”。

**Acceptance Criteria:**
- [ ] 每条硬条件输出 `pass`、`fail` 或 `unknown`，并引用 JD 与候选人证据。
- [ ] 只有显式、可机器验证且有证据冲突的条件可判定 fail。
- [ ] 信息缺失、证据不足或 LLM 不确定必须为 unknown，不能自动判 fail。
- [ ] 硬条件结果与软评分分开保存和展示。
- [ ] 任意排除结论必须提示人工确认。

### US-006: LLM 多维匹配分析

**Description:** 作为招聘人员，我希望从多个岗位相关角度评估候选人，以便理解总分背后的优势和差距。

**Acceptance Criteria:**
- [ ] 初始维度和权重为：技能 30、职责 20、相关经验 15、职级/范围 10、项目证据 10、工程/架构 10、领域 5。
- [ ] 每个维度输出分数、状态、理由、JD evidence IDs、candidate evidence IDs 和置信度。
- [ ] LLM 只能引用 Source Catalog 中存在的证据 ID；未知 ID 使结果校验失败。
- [ ] 无足够证据的维度为 unknown；证据覆盖不足时总分为空且建议为 manual_review。
- [ ] 最终 recommendation 由服务端确定性规则计算，不接受 LLM 自由决定。

### US-007: 异步、可重试、可追溯的匹配

**Description:** 作为招聘人员，我希望耗时匹配可查看进度、失败原因和历史，以便安全重试并比较结果。

**Acceptance Criteria:**
- [ ] `hybrid_v2` 使用异步 run，状态覆盖 queued/running/ready/failed/stale。
- [ ] 相同输入 fingerprint 与 matcher version 的重复请求复用结果或活动 run。
- [ ] 旧 worker 不得覆盖更新后的输入或新 run。
- [ ] 结果记录 matcher、schema、Prompt、provider、model、JD revision 和 Profile/Facts revision。
- [ ] 旧 `POST /jd/match` 继续提供 `rules_v1` 兼容结果。

### US-008: 查看和重新计算匹配结果

**Description:** 作为招聘人员，我希望在 JD 详情页查看完整匹配分析并在结果过期时重新计算。

**Acceptance Criteria:**
- [ ] 页面显示 hard filters、总分、维度、证据、风险、缺口、置信度和 recommendation。
- [ ] 页面覆盖 empty、loading、processing、ready、failed、stale 和 retry pending。
- [ ] stale 状态显示原因；重新计算期间禁止重复提交。
- [ ] 中英文文案同步，并进行桌面与移动端浏览器验证。

### US-009: 下游只消费 fresh 结果

**Description:** 作为求职计划或面试流程使用者，我希望下游只使用与当前输入一致的匹配结果，以免生成过时建议或问题。

**Acceptance Criteria:**
- [ ] JD 结构化 revision、Resume/Profile/Facts revision、matcher/Prompt/schema/model 版本变化均触发 freshness 重新判断。
- [ ] 求职计划 snapshot 保存所用 match result 和输入 fingerprint。
- [ ] 面试可选接收 `jd_id`/`match_result_id`，同时保留旧 `jd_text` 兼容路径。
- [ ] stale 结果可历史查看，但不得被下游标记为 fresh。

### US-010: 文档与交付可追溯

**Description:** 作为维护者，我希望 PRD、SPEC、issues、代码和测试具有一一对应关系，以便后续会话不会依据过时文档实现错误功能。

**Acceptance Criteria:**
- [ ] RIP-003 明确当前是 `rules_v1`，不是 LLM/向量多维匹配。
- [ ] RIP-007、RIP-008 区分“代码存在”和“已验收”。
- [ ] 每条 FR 映射到 SPEC、issue 和测试边界。
- [ ] issue 完成时同步 tasks、current 状态、测试证据和 as-built 设计。

## 5. Functional Requirements

- FR-1: 系统必须提供独立的多图片 JD 导入接口，并保留现有导入接口。
- FR-2: 系统必须校验扩展名、声明 MIME、magic bytes、文件大小、图片数量、像素数和最大边长。
- FR-3: 系统必须使用 `processing_run_id` 保护图片处理任务不被旧 worker 写回。
- FR-4: 系统必须通过显式 capability 判断当前 LLM 配置能否接收图片。
- FR-5: 系统必须使用统一多模态消息模型，由 provider adapter 转换为供应商协议。
- FR-6: 系统必须先完成 Vision 文本转写，再调用现有文本 JD 结构化抽取器。
- FR-7: 系统必须保存图片顺序、对象引用、校验信息、转写状态、模型和版本，不在业务表保存图片 base64。
- FR-8: 系统必须在转写文本质量不足时失败，不得静默生成空 JD。
- FR-9: 系统必须对 Vision 调用设置独立超时、有限重试和安全错误映射。
- FR-10: 系统必须允许人工编辑 Vision 来源的结构化字段并保护人工来源。
- FR-11: 系统必须把硬条件表示为有类型、有运算符、有 JD evidence 的结构化条件。
- FR-12: 系统必须只对显式可验证条件执行硬筛选。
- FR-13: 系统必须将硬筛选的 `unknown` 与 `fail` 分开处理。
- FR-14: 系统必须从已脱敏 Resume Facts/Profile 构建稳定 Source Catalog。
- FR-15: 系统不得向匹配 LLM 发送原始简历全文或 identity 字段。
- FR-16: 系统必须按七个初始维度返回结构化 LLM 评分和证据引用。
- FR-17: 系统必须拒绝引用未知证据 ID、越界分数或缺少必需字段的 LLM 输出。
- FR-18: 系统必须由确定性策略聚合分数并产生 screening recommendation。
- FR-19: 系统必须在证据覆盖不足或硬条件 unknown 时返回 `manual_review`。
- FR-20: 系统必须版本化保存输入 fingerprint、算法、Prompt、schema、provider 和 model。
- FR-21: 系统必须提供异步创建/查询/重算匹配接口，并保留 `POST /jd/match` 的 `rules_v1` 语义。
- FR-22: 系统必须在相同输入和 matcher version 下保证幂等。
- FR-23: 系统必须在 JD、Resume Facts/Profile 或匹配版本变化时将旧结果判定为 stale。
- FR-24: 系统必须允许查看 stale 历史，但下游不得把它当作 fresh 输入。
- FR-25: 前端必须完整展示图片导入和匹配的异步状态、失败、重试与过期状态。
- FR-26: 求职计划必须把 matcher/model/prompt/schema 和输入 revision 纳入 freshness。
- FR-27: 面试的新 `jd_id`/`match_result_id` 输入必须是可选扩展，不能破坏现有 `jd_text` 调用。
- FR-28: 所有日志、错误响应、测试 fixture 和截图必须使用安全摘要或合成数据。
- FR-29: Vision 图片发送前必须向用户明确披露图片会交给其配置的外部模型；现有文本 PrivacyGuard 不得被描述为可检查图片像素。
- FR-30: 每个实现 issue 必须引用对应 PRD、SPEC 和验收测试。

## 6. Non-Goals

- 不引入本地 OCR 作为首版主链路；图片文字由用户要求的 Vision LLM 读取。
- 不在本期支持 GIF、SVG、TIFF、HEIC 或任意视频输入。
- 不在本期引入 Qdrant、embedding、RAG 或向量召回。
- 不让 LLM 自由决定淘汰、录用或最终招聘结论。
- 不实现认证、多租户、RBAC 或生产级对象访问控制。
- 不把整个 JD、Resume、Plan 或 Interview 模块重写为 Agent。
- 不承诺所有自定义 OpenAI-compatible endpoint 均支持图片。

## 7. Design Considerations

- 图片入口复用现有 `JDImportDialog` 与 JD Detail，不新建孤立页面。
- 转写完成后先展示可编辑结构化结果；用户可纠正图片误读。
- 匹配结果优先展示证据和不确定性，不把单一百分比作为唯一结论。
- `fail`、`unknown`、`missing evidence` 使用不同视觉语义，避免误读。

## 8. Technical Considerations

- 继续使用 FastAPI、Celery、PostgreSQL、Redis、MinIO 和现有 LLM gateway/provider adapter。
- 建议限制：最多 8 张；单张 10MB；总计 30MB；单张 25MP；最大边 4000px。
- 图片与转写拆分存储：`jd_source_assets` 保存有序资源元数据，`job_descriptions.raw_text` 保存拼接后的转写正文。
- Vision 原图会发送给外部 provider，这是产品明确授权的边界；日志和持久化必须最小化，原图保留策略必须可配置且有删除路径。
- 匹配结果先使用 JSONB 保存维度和证据，避免首版拆成大量关系表；查询字段使用普通列和索引。

## 9. Success Metrics

- 合成图片 JD 的导入成功率达到 95% 以上，且 100% 成功结果可进入人工编辑。
- 所有 ready 的 `hybrid_v2` 结果都通过 evidence ID 校验，无悬空引用。
- JD/Profile/算法版本变化的 freshness 矩阵测试 100% 通过。
- 旧文本/文件/URL 导入和 `rules_v1` 匹配回归测试全部通过。
- 不出现图片 base64、原始简历或直接标识符进入日志/错误响应的测试泄露。

## 10. Open Questions and Assumptions

- [Assumption] 首版图片来源是招聘岗位截图，不是候选人简历图片。
- [Assumption] 首版允许把原始 JD 图片发送给用户主动配置的外部 Vision provider，并在 UI 显示披露。
- [Assumption] 扫描 PDF 的 Vision 回退在 RIP-010 验收后单独开启，不阻塞纯图片导入。
- [Assumption] 多维权重作为 `matcher_version` 的一部分配置在代码中，首版不提供任意 UI 调权。
- [Assumption] 硬条件由结构化 JD 中明确表达的条件产生；推测性条件不能作为 hard filter。
- [Assumption] 本期 recommendation 是人工筛选辅助，不触发自动通知、自动淘汰或外部招聘系统动作。

## 11. Delivery Slices

| Spec | Scope | Depends On |
|---|---|---|
| RIP-010 | JD 图片上传、Vision 能力、转写、结构化复用及导入 UI | RIP-007 |
| RIP-011 | 证据约束的多维匹配、硬筛选、版本化结果及异步 API | RIP-002, RIP-003, RIP-009, RIP-010 |
| RIP-012 | 匹配结果 UI、freshness、Plan/Interview 消费与端到端验收 | RIP-008, RIP-011 |

## 12. Requirement Traceability

| PRD requirements | Primary SPEC | Implementation issues |
|---|---|---|
| FR-1~FR-5 | RIP-010 Sections 6.2, 6.4, 7.1, 9~10 | #093, #094 |
| FR-6~FR-10 | RIP-010 Sections 6.3, 7.1~7.3 | #095, #097 |
| FR-11~FR-13 | RIP-011 Sections 6.2, 6.4 | #098, #099 |
| FR-14~FR-19 | RIP-011 Sections 6.3~6.4, 7.1 | #099, #100 |
| FR-20~FR-24 | RIP-011 Sections 6.5, 7, 9~10 | #098, #101, #102 |
| FR-25 | RIP-010 Section 11; RIP-012 Sections 6.2, 7.1 | #096, #103 |
| FR-26 | RIP-012 Sections 6.1, 7.2 | #104 |
| FR-27 | RIP-012 Sections 7.3, 9.3~10 | #105 |
| FR-28~FR-29 | RIP-010 Section 7.3; RIP-011 Sections 6.1, 7.2; RIP-012 Section 7.3 | #093~#106 acceptance/privacy scopes |
| FR-30 | All three SPEC Definitions of Done | #092, #097, #102, #106 |
