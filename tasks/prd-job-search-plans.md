# PRD: AI 求职计划列表

## 1. Introduction / Overview

当前系统可以解析简历、生成 Candidate Profile，并计算简历与 JD 的匹配结果，但尚未把差距分析转化为可持续执行的行动方案。用户能够看见“缺什么”，却无法在系统内规划“接下来做什么”。

本功能新增独立的“计划列表”。用户选择一个状态为 ready 的 JD 和一份已完成解析的简历，系统结合 JD 结构化结果、Candidate Profile 与 JD Match Result 生成综合求职计划。计划同时覆盖能力补强、求职材料准备、面试训练、投递执行与复盘，生成后允许用户增删改任务、排序、设置优先级和截止日期、更新完成状态及重新生成。

## 2. Goals

- 将 JD 与候选人背景的差距转化为具体、可执行、可跟踪的任务。
- 每份计划严格关联一个 JD 和一份简历/候选人画像。
- 计划同时覆盖能力准备与求职执行，而不是只输出泛化学习建议。
- 支持任务增删改、排序、状态、优先级、截止日期和重新生成。
- 让每条 AI 建议能够追溯到 JD 要求、Candidate Profile 或匹配结果。
- 覆盖空、生成中、成功、失败和重试状态。

## 3. User Stories

### US-001: 持久化计划及任务

**Description:** As a user, I want plans and tasks to persist so that I can execute them across multiple sessions.

**Acceptance Criteria:**
- [ ] 计划记录包含名称、`jd_id`、`resume_id`、匹配结果引用、目标日期、每周可投入时间、补充背景、状态、生成模型、创建时间和更新时间
- [ ] 计划状态至少包含 `generating`、`active`、`completed` 和 `failed`
- [ ] 任务记录包含标题、类别、行动说明、生成依据、来源、优先级、状态、截止日期和排序位置
- [ ] 任务来源至少区分 `ai` 和 `manual`
- [ ] 任务状态至少包含 `todo`、`in_progress` 和 `done`
- [ ] 数据库迁移、后端单测、lint 和 typecheck 通过

### US-002: 选择 JD 与简历创建计划

**Description:** As a user, I want to choose one JD and one resume so that the generated plan targets a concrete role and my actual background.

**Acceptance Criteria:**
- [ ] 创建流程只能选择状态为 `ready` 的 JD
- [ ] 创建流程只能选择已经生成 Candidate Profile 的简历
- [ ] 用户可以填写目标日期、每周可投入时间和补充背景信息
- [ ] 缺少 JD 或简历时生成按钮不可用，并提供进入对应创建流程的入口
- [ ] 提交后立即创建 `generating` 计划并进入进度或详情视图
- [ ] [Assumption] 同一 `jd_id + resume_id` 同时只允许存在一份未完成计划；重复创建时返回已有计划入口
- [ ] 前端 typecheck 和浏览器验证通过

### US-003: 生成综合求职计划

**Description:** As a user, I want AI to turn my JD match gaps into a comprehensive plan so that I know what to improve and what actions to take.

**Acceptance Criteria:**
- [ ] 生成前获取或创建当前 JD 与简历的 JD Match Result
- [ ] 计划至少包含“差距优先级、简历优化、技能补强、项目/经历梳理、面试准备、投递与复盘”六类任务
- [ ] 每个 AI 任务包含明确动作、优先级、建议截止日期和生成依据
- [ ] 生成依据引用 JD 要求、Candidate Profile 或 JD Match Result 中的具体信息
- [ ] 系统不得把 Candidate Profile 中不存在的信息描述为用户已有经历
- [ ] 信息不足时任务必须标注为“待用户补充”或“建议验证”，不得编造背景
- [ ] 生成成功后计划状态变为 `active`
- [ ] 生成失败后计划状态变为 `failed`，输入不丢失并提供重试入口
- [ ] 单测覆盖正常生成、输入缺失、LLM 非法输出和 LLM 失败路径

### US-004: 查看并执行计划

**Description:** As a user, I want to see prioritized tasks and progress so that I can execute the plan day by day.

**Acceptance Criteria:**
- [ ] 详情页展示关联 JD、关联简历、总体进度和按类别组织的任务
- [ ] 用户可以将任务状态修改为待办、进行中或已完成
- [ ] 用户可以修改标题、行动说明、类别、优先级和截止日期
- [ ] 用户可以新增人工任务、删除未完成任务并调整任务顺序
- [ ] 所有修改自动保存；保存失败时恢复可编辑状态并保留未提交内容
- [ ] [Assumption] 总体进度按已完成任务数除以有效任务总数计算
- [ ] 刷新页面后任务内容、顺序和状态保持不变
- [ ] 前端 typecheck 和浏览器验证通过

### US-005: 重新生成计划

**Description:** As a user, I want to regenerate unfinished AI tasks so that the plan can respond to updated inputs without losing completed work.

**Acceptance Criteria:**
- [ ] 重新生成前显示影响范围和确认对话框
- [ ] 已完成任务必须保留
- [ ] `source=manual` 的人工任务必须保留
- [ ] 仅未完成且 `source=ai` 的任务可以被替换
- [ ] 重新生成使用最新 JD、Candidate Profile、匹配结果和计划偏好
- [ ] 关联 JD 或简历不可用时阻止重新生成并显示具体原因
- [ ] 重新生成失败时恢复原任务集合，不产生半更新状态
- [ ] 后端单测和浏览器验证通过

### US-006: 查看和筛选计划列表

**Description:** As a user, I want to scan all plans and their progress so that I can decide what to work on next.

**Acceptance Criteria:**
- [ ] `/plans` 展示计划名称、目标岗位、公司、关联简历、进度、下一个截止任务、状态和更新时间
- [ ] 列表支持按计划名称、岗位或公司关键词搜索
- [ ] 列表支持按计划状态筛选
- [ ] 默认按最近更新时间倒序排列
- [ ] 删除计划前显示确认对话框，取消时不发送删除请求
- [ ] 页面分别提供空、加载、生成中、成功和加载失败状态
- [ ] 中英文文案、前端 typecheck 和浏览器验证通过

### US-007: 从现有资产进入计划流程

**Description:** As a user, I want to create a plan from an existing JD or resume so that the workflow remains connected.

**Acceptance Criteria:**
- [ ] JD 详情页的“创建计划”入口预选当前 JD
- [ ] 简历列表或详情页的“创建计划”入口预选当前简历
- [ ] 若只预选一项，创建页要求用户选择另一项后才能生成
- [ ] 创建完成后返回计划详情，不要求用户重新选择相同输入
- [ ] 集成测试覆盖从 JD 和简历两侧进入计划创建的路径
- [ ] 浏览器验证通过

## 4. Functional Requirements

- FR-1: 系统必须提供计划列表、详情、创建、更新、删除、重试和重新生成接口。
- FR-2: 每份计划必须关联一个 `jd_id`。
- FR-3: 每份计划必须关联一个 `resume_id`。
- FR-4: 系统必须在创建计划前验证 JD 状态为 `ready`。
- FR-5: 系统必须在创建计划前验证简历存在 Candidate Profile。
- FR-6: 系统必须允许用户填写目标日期、每周可投入时间和补充背景。
- FR-7: 系统必须使用 JD 结构化结果、Candidate Profile 和 JD Match Result 生成计划。
- FR-8: 系统必须保存计划生成时使用的匹配结果引用和 LLM 模型信息。
- FR-9: 系统必须为 AI 任务保存生成依据。
- FR-10: 系统必须将缺乏输入证据的建议标记为待补充或待验证。
- FR-11: 系统必须允许用户新增人工任务。
- FR-12: 系统必须允许用户编辑任务内容、类别、优先级、状态和截止日期。
- FR-13: 系统必须允许用户调整任务顺序。
- FR-14: 系统必须持久化每次任务修改。
- FR-15: 系统必须按已完成任务数计算 MVP 计划进度。
- FR-16: 重新生成必须保留已完成任务。
- FR-17: 重新生成必须保留人工任务。
- FR-18: 重新生成只能替换未完成的 AI 任务。
- FR-19: 重新生成失败时系统必须保留原任务集合。
- FR-20: 计划列表必须支持关键词、状态筛选和更新时间排序。
- FR-21: 计划生成失败时系统必须保留生成输入和失败原因。
- FR-22: 同一 JD 与简历组合不得同时创建重复的未完成计划。
- FR-23: 系统不得允许脱离 JD 或简历创建空白计划。

## 5. MVP Scope Boundary

本期只交付“基于一个 JD 和一份简历生成、编辑、执行及重新生成计划”的完整闭环。以下能力不进入本期验收，但不是永久排除项，已进入后续 TODO。

## 6. Post-MVP TODO

| TODO | 后续能力 | 本期状态 | 后续补充方向 |
|---|---|---|---|
| TODO-PLAN-001 | 日历同步 | 不实现 | 将任务截止日期同步至外部日历，并处理更新与取消 |
| TODO-PLAN-002 | 消息提醒 | 不实现 | 增加站内或外部渠道的到期、逾期和进度提醒 |
| TODO-PLAN-003 | 自动投递 | 不实现 | 在获得用户明确授权后对接招聘渠道与投递材料 |
| TODO-PLAN-004 | 招聘流程跟踪 | 不实现 | 跟踪已投递、沟通、笔试、面试、Offer 和关闭状态 |
| TODO-PLAN-005 | 多人共享 | 不实现 | 支持导师、同伴或顾问查看、评论和协作编辑计划 |
| TODO-PLAN-006 | 完整版本历史 | 不实现 | 保存每次生成与编辑版本，支持差异查看和恢复 |
| TODO-PLAN-007 | 课程内容生成 | 不实现 | 根据技能差距生成系统课程、练习和学习材料 |
| TODO-PLAN-008 | 无 JD/简历的空白计划 | 不实现 | 支持用户从空白模板手工建立通用计划 |

## 7. Design Considerations

- 顶部导航在截图标注区域增加“计划列表”，与“JD 列表”并列。
- 计划列表保持工作型信息密度，重点展示进度、状态和下一个行动，不使用营销式大卡片。
- 创建流程使用明确的 JD 选择器、简历选择器和少量计划偏好字段。
- 任务状态使用选择控件或复选框，优先级使用明确标记，排序使用稳定的拖动手柄或上下移动命令。
- 生成、保存和重新生成期间保持布局稳定，不让加载文字改变任务面板尺寸。
- 删除和重新生成必须使用确认对话框。

## 8. Technical Considerations

- 新建独立 Plan 领域及持久化模型，不把计划 JSON 塞入 JD、Resume 或 Candidate Profile。
- 计划生成编排依赖现有 JD Matching；已有匹配结果可复用，需要时再生成新的匹配结果。
- LLM 输出必须通过结构化 schema 校验；校验失败可以在内部重试一次，仍失败则将计划标记为 `failed`。
- 重新生成应在事务中构建替换集合，只有完整成功后才切换未完成 AI 任务。
- 任务的 `source` 与 `basis` 字段必须独立，避免人工任务被误删或 AI 建议失去依据。
- 列表及详情数据由后端持久化提供，不依赖 localStorage 作为数据源。

## 9. Success Metrics

- 用户选择一个 ready JD 和一份有效简历后，可以在同一流程中生成计划。
- 成功生成的计划覆盖六类约定任务，并为 AI 任务提供可查看的生成依据。
- 用户编辑任务后刷新页面，内容、顺序、状态和截止日期均不丢失。
- 重新生成不会删除已完成任务或人工任务。
- 任一生成失败状态都保留输入、显示具体错误并提供重试。
- 所有新增后端测试、前端 typecheck、lint 和浏览器验收通过。

## 10. Open Questions

- 后续若允许同一 JD 与简历组合存在多份计划，应通过计划目标区分，还是引入归档状态？
- 引入任务权重后，计划进度是否需要从数量占比迁移为权重占比？

