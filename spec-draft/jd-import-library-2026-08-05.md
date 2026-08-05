# PRD: JD 导入与职位资料库

**Status**: Approved for specification

**Prepared**: 2026-08-05

**Program**: `spec-draft/job-target-interview-program-2026-08-05.md`

**Sources**: `spec-draft/career-agent-product-direction-2026-08-04.md`, `spec-draft/career-agent-workflow-2026-08-05.md`

**Existing baseline**: RIP-003、RIP-007

## 1. Introduction / Overview

现有 JD 资料库已经支持粘贴文本、上传文件和导入公开网页，并能异步抽取部分结构化字段、检测重复、编辑结果和重试失败任务。但当前结构化字段仍较少，ready 记录会被直接修改，历史匹配和面试无法稳定引用“当时使用的 JD 内容”。图片和纯手工创建也尚未进入统一流程。

本功能把 JD 资料库升级为可审核、可发布、可追溯的职位输入模块。用户可以通过五种方式获得原始内容，系统完成本地读取、标准化、结构化解析和证据定位；用户确认后发布一个不可变 JD Version。后续修正或重新解析会形成新版本，不改变已有匹配、面试方案或报告的含义。

保存 JD 只代表进入资料库，不自动将其设为目标岗位。Job Target 在首次匹配、创建面试方案或创建求职计划时再按需建立。

## 2. Goals

- 在一个统一流程中支持文本、文件、图片、公开链接和手动表单五种 JD 输入方式。
- 为结构化岗位信息提供字段级证据、置信度和人工确认入口。
- 将用户确认的结果发布为不可变 JD Version，使历史下游结果可重放、可解释。
- 让抽取、审核、失败、重复和归档状态在列表与详情中清晰可恢复。
- 复用现有 RIP-007 导入、MinIO、解析器、SafeWebFetcher、JDExtractor 和 Celery 能力。
- 保持现有 `/api/v1/jd` 调用方可迁移，不在本功能中重写匹配或面试逻辑。

## 3. User Stories

### US-001: 通过五种方式创建 JD

**Description:** As a 求职用户, I want to 用最适合当前来源的方式录入 JD so that 招聘网站、文件、截图和零散信息都能进入同一资料库。

**Acceptance Criteria:**

- [ ] 创建入口提供“粘贴文本、上传文件、上传图片、公开链接、手动填写”五个互斥模式。
- [ ] 文件模式接受 PDF、DOCX、TXT 和 Markdown，并沿用 10MB 上限。
- [ ] 图片模式接受产品确认的 PNG/JPEG 类型，并在提交前显示文件名、类型和大小。
- [ ] 链接模式只接受无凭证段的公开 HTTP/HTTPS URL，并明确提示登录态或受限页面可能失败。
- [ ] 手动模式至少允许填写岗位名称、公司、职责、必备技能和备注；岗位名称为唯一必填业务字段。
- [ ] 当前模式输入无效时提交按钮禁用，切换模式不会把另一模式的内容误提交。
- [ ] 中英文文案、前端 typecheck、lint 通过。
- [ ] 使用可用的浏览器控制技能完成桌面和移动端验收。

### US-002: 记录来源并异步处理内容

**Description:** As a 用户, I want to 看见 JD 当前处理到哪一步 so that 我能区分读取、解析、审核和失败，而不是面对一个无期限 spinner。

**Acceptance Criteria:**

- [ ] 通过基础校验后先持久化 JD 身份和来源，再派发异步处理。
- [ ] 处理中的记录展示当前步骤，至少区分 `source_extract` 和 `structure_parse`。
- [ ] 文件和图片保留安全的对象存储引用，网页保留规范化 URL，文本和手工来源保留对应来源类型。
- [ ] 每次处理携带独立 run ID，旧 run 不能覆盖重试或重新解析产生的新结果。
- [ ] broker 派发失败时记录可重试失败状态，不把记录伪装成 processing。
- [ ] 页面卸载、隐藏或进入终态后停止轮询；超时后展示恢复操作。
- [ ] 后端单元与集成测试覆盖创建、派发失败、超时和 stale run。

### US-003: 提取结构化职位信息和证据

**Description:** As a 用户, I want to 检查系统从原文识别出的岗位信息和证据 so that 我能判断结果是否可信。

**Acceptance Criteria:**

- [ ] 结构化结果覆盖岗位名称、公司、部门、地点、用工类型、职级、薪资、经验年限、学历、岗位职责、必备技能和加分技能。
- [ ] 结构化结果覆盖行业/业务上下文、语言要求、证书、领域经验和面试线索。
- [ ] 每项职责、技能和硬性要求尽可能保存原文 evidence 与 confidence；没有证据时不得生成伪造引用。
- [ ] 无法从来源确认的标量字段返回空值，无法确认的列表返回空列表。
- [ ] LLM 输出必须通过 Pydantic v2 结构校验和字段数量/长度限制。
- [ ] 结构化输出保存 parser version、model、schema version 和 overall confidence。
- [ ] 输入文本中的指令被视为不可信内容，不能改变抽取任务或系统规则。
- [ ] 使用合成 JD fixture 覆盖完整、缺字段、矛盾字段和恶意指令场景。

### US-004: 审核并修正识别结果

**Description:** As a 用户, I want to 对照原文修正低置信度或错误字段 so that 下游流程使用我确认过的数据。

**Acceptance Criteria:**

- [ ] 抽取完成后进入 `needs_review`，不会未经用户确认直接发布新版本。
- [ ] 详情页可对照查看原始内容、结构化字段、字段证据和置信度。
- [ ] 用户可修改本 PRD 定义的结构化业务字段，但不能在结构化编辑器中改写原始来源内容。
- [ ] 被人工修改的字段标记为 `manual`，未修改字段保留 `llm` 或 `source` 来源。
- [ ] 保存失败时保留本地编辑内容并提供重试，取消编辑不发送写请求。
- [ ] 并发修改冲突必须要求刷新或重新应用，不能静默覆盖另一标签页的结果。
- [ ] 低置信度、字段冲突和缺少关键字段在确认前有可见提示。
- [ ] 使用可用的浏览器控制技能完成桌面和移动端验收。

### US-005: 发布不可变 JD Version

**Description:** As a 用户, I want to 发布一个确定的 JD 版本 so that 后续匹配和面试始终引用同一份输入。

**Acceptance Criteria:**

- [ ] 用户确认审核结果后，系统在一个事务中创建不可变 JD Version 并将其标记为 ready。
- [ ] JD Version 包含规范化原文、结构化内容、证据、来源元数据、content hash、parser/model/schema version 和确认时间。
- [ ] 已发布版本不提供 PATCH；任何修正必须从该版本创建新的可审核草稿。
- [ ] JD 详情明确显示当前版本号、版本状态和发布时间。
- [ ] ready JD 的下游入口传递 `jd_version_id`，不能只传可变的 `jd_id` 或复制 `raw_text`。
- [ ] 发布重复请求具备幂等性，不产生两个内容相同的版本。
- [ ] 数据库测试证明旧版本在发布新版本后内容保持不变。

### US-006: 查看版本历史并重新解析

**Description:** As a 用户, I want to 查看 JD 历史版本并基于原来源重新解析 so that 我能升级结构而不破坏历史结果。

**Acceptance Criteria:**

- [ ] 详情页列出版本号、状态、创建原因、parser/schema version、确认时间和是否为当前版本。
- [ ] 用户可以打开任一历史版本的只读原文、结构化结果和证据。
- [ ] 重新解析创建新的 processing run 和草稿版本，不修改任何 ready 历史版本。
- [ ] 默认保护人工字段；用户明确选择覆盖时才允许新的抽取结果替换人工值。
- [ ] 重新解析失败时当前 ready 版本继续可用，失败草稿提供重试或放弃操作。
- [ ] 历史版本已被匹配或面试引用时仍可读取，不因 JD 归档而删除。
- [ ] 使用可用的浏览器控制技能验证版本切换、失败恢复和刷新持久化。

### US-007: 处理重复、失败和归档

**Description:** As a 用户, I want to 识别重复内容并恢复失败记录 so that 资料库不会因为误操作变得混乱。

**Acceptance Criteria:**

- [ ] 相同规范化 URL、文件 hash 或正文 hash 触发 `duplicate_pending`，并展示已存在记录的安全摘要。
- [ ] 用户可以取消重复导入或明确保留为另一条 JD 身份。
- [ ] source extraction 和 structure parsing 失败分别保存安全错误码、失败步骤和 retryable 标记。
- [ ] retry 从可复用的最近安全步骤重新开始，并生成新的 run ID。
- [ ] 用户可以归档 JD；归档不删除历史版本和下游引用。
- [ ] 被 Job Target、计划、匹配或面试引用的 JD 不允许硬删除。
- [ ] 原始异常、provider 响应、密钥和网页 HTML 不出现在 API 错误或持久化业务错误中。

### US-008: 浏览资料库并进入下游流程

**Description:** As a 用户, I want to 从 JD 列表快速找到目标岗位并选择一个 ready 版本 so that 我可以继续匹配或面试准备。

**Acceptance Criteria:**

- [ ] 列表展示岗位、公司、地点、来源、当前版本、状态和更新时间。
- [ ] 列表支持岗位/公司关键词、来源、状态和标签筛选，并默认按最近更新时间倒序。
- [ ] 列表与详情分别覆盖 loading、empty、success、failure、processing、needs_review 和 archived 状态。
- [ ] 只有存在 ready 版本时显示“匹配简历”“创建面试方案”“创建求职计划”入口。
- [ ] 下游动作默认使用当前 ready 版本，并允许用户在后续选择页切换历史 ready 版本。
- [ ] 首次下游动作才创建或取得 Job Target；仅浏览、编辑或发布 JD 不创建工作区。
- [ ] 中英文文案、前端 typecheck、lint 通过。
- [ ] 使用可用的浏览器控制技能完成桌面和移动端验收。

## 4. Functional Requirements

- FR-1: 系统必须支持粘贴文本创建 JD。
- FR-2: 系统必须支持从 PDF、DOCX、TXT 和 Markdown 文件创建 JD。
- FR-3: 系统必须支持从 PNG 和 JPEG 图片创建 JD。
- FR-4: 系统必须支持从公开 HTTP/HTTPS URL 创建 JD。
- FR-5: 系统必须支持通过结构化表单手动创建 JD。
- FR-6: 系统必须在异步处理开始前持久化 JD 身份和来源。
- FR-7: 系统必须为每次异步处理分配 run ID。
- FR-8: 系统必须拒绝 stale run 写入。
- FR-9: 系统必须将上传对象保存在现有 MinIO 边界内。
- FR-10: 系统必须对公开 URL 应用现有 SSRF、重定向、MIME、大小和超时限制。
- FR-11: 系统必须将图片 OCR 依赖关联到现有 OCR parser 交付，而不是在 JD 模块内复制 OCR 引擎。
- FR-12: 系统必须输出本 PRD 定义的结构化职位字段。
- FR-13: 系统必须为可定位字段保存 evidence 和 confidence。
- FR-14: 系统必须将不确定字段保留为空。
- FR-15: 系统必须在发布前进入用户审核状态。
- FR-16: 系统必须记录字段来源为 source、llm 或 manual。
- FR-17: 系统必须将确认结果发布为不可变 JD Version。
- FR-18: 系统必须为 JD Version 保存 content hash 和生成版本信息。
- FR-19: 系统必须通过 `jd_version_id` 向下游传递 ready 输入。
- FR-20: 系统必须通过新草稿版本处理已发布内容的修正。
- FR-21: 系统必须保留所有被下游资源引用的历史版本。
- FR-22: 系统必须检测规范化 URL、文件和正文重复。
- FR-23: 系统必须允许用户确认保留疑似重复记录。
- FR-24: 系统必须支持失败重试和 ready 版本重新解析。
- FR-25: 系统必须允许归档 JD 身份。
- FR-26: 系统必须阻止删除仍有下游引用的 JD。
- FR-27: 系统必须提供分页、搜索、来源、状态和标签筛选。
- FR-28: 系统必须在所有用户可见错误中使用安全错误信息。
- FR-29: 系统必须在首个下游动作之前保持 Job Target 不存在。

## 5. Non-Goals

- 不支持需要登录、验证码、浏览器扩展或绕过反爬机制的招聘页面。
- 不支持招聘平台持续同步、岗位变更监控或批量爬取。
- 不在本功能中实现通用 OCR 平台；图片导入复用 issue #030 的 parser 能力。
- 不在本功能中计算简历匹配分或生成面试题。
- 不在 JD 保存或发布时自动创建 Job Target。
- 不支持多人协作审核、共享或权限控制。
- 不保存网页 HTML 快照，不执行来源页面脚本。
- 不引入 Qdrant、RAG、Embedding 或公司知识库。

## 6. Design Considerations

- 保持现有 `/jobs` 列表和 `/jobs/:id` 详情路由，避免为版本历史另建平行资料库。
- 导入方式使用分段控件；处理状态使用统一状态标记；字段 evidence 在对应字段附近展示。
- 原文和结构化内容使用可对照的页内布局，不把审核隐藏在多层弹窗中。
- 版本历史为只读列表或标签视图；当前版本和草稿必须有明显区分。
- 删除、放弃草稿、覆盖人工字段和归档使用确认对话框。
- 图片、文件和 URL 的错误文案说明用户下一步，不展示后端异常对象。

## 7. Technical Considerations

- 扩展现有 JD bounded context，不新建第二套 JD 聚合或通用导入框架。
- `job_descriptions` 保留稳定身份和来源关系；正式 SPEC 定义不可变 `job_description_versions`、草稿/publish 事务和旧数据 v1 回填。
- 当前可变 JD 字段在兼容期继续服务旧接口，但新下游契约以 version resource 为规范来源；兼容字段移除必须另有 issue。
- 图片处理通过现有 parser factory 或明确 application port 调用 OCR 能力，不直接依赖 OCR provider SDK。
- 外部网络、文件解析和 LLM 调用不得持有数据库事务。
- API 继续使用 `/api/v1` 和统一 `APIResponse` envelope；二进制/multipart 仍留在 JD feature client。
- 数据库与保留策略变化必须同步 Alembic migration、`design/database.md` 和回滚说明。

## 8. Success Metrics

- 五种输入方式都能完成“创建 -> 处理 -> 审核 -> 发布 -> 查看版本”的可恢复流程。
- 100% 的匹配和面试入口传递具体 `jd_version_id`。
- 发布新版本后，引用旧版本的集成测试结果保持不变。
- 所有结构化硬性要求都包含 evidence，或明确标记 evidence unavailable。
- 处理失败不会丢失可安全保留的来源信息，并能从正确步骤重试。
- 所有后端、迁移、前端静态检查和浏览器验收达到仓库质量门禁。

## 9. Open Questions

当前无阻塞产品问题。正式 SPEC 阶段需要以实际 Alembic head、issue #030 的 OCR contract 和现有 JD API 调用方为准确定迁移与兼容细节。
