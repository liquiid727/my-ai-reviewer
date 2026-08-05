# PRD: JD 列表与智能识别

## 1. Introduction / Overview

当前系统已经具备 JD 创建、LLM 结构化抽取、简历匹配和匹配结果查询能力，但缺少面向用户的 JD 资料库。用户只能在单次流程中临时输入 JD，无法集中查看、修正、复用或管理目标岗位。

本功能新增独立的“JD 列表”。用户可以粘贴 JD 文本、上传 JD 文件或填写公开招聘网页链接。系统提取原始文本后调用现有 JD Extractor 识别结构化信息并自动保存；用户随后可以查看原文、修正结果、重新识别，并将已有 JD 用于简历匹配或求职计划生成。

## 2. Goals

- 建立可持久化、可编辑、可复用的个人 JD 资料库。
- 支持文本、文件和公开网页链接三种 JD 录入方式。
- 复用现有 JD Extractor、JD Matching 和 LLM Gateway，不重复建设匹配引擎。
- 保留原始内容、来源信息和抽取证据，使 LLM 结果可检查、可修正。
- 为每条 JD 提供空、处理中、成功、失败和重试状态。
- 从 JD 详情直接进入“匹配简历”和“创建计划”流程。

## 3. User Stories

### US-001: 持久化 JD 记录及处理状态

**Description:** As a user, I want every submitted JD to become a persistent record so that I can return to it even if extraction is still running or has failed.

**Acceptance Criteria:**
- [ ] JD 记录包含标题、公司、原文、录入来源、来源地址或文件元数据、处理状态、错误信息、创建时间和更新时间
- [ ] 处理状态至少包含 `processing`、`ready` 和 `failed`
- [ ] 文本、文件或链接通过基础校验后，系统先创建记录，再执行内容提取和 LLM 识别
- [ ] 识别失败时保留记录、原始输入和可操作的错误信息
- [ ] 数据库迁移、后端单测、lint 和 typecheck 通过

### US-002: 通过三种来源录入并识别 JD

**Description:** As a user, I want to submit a JD as text, a file, or a public web link so that I do not need to manually normalize its content.

**Acceptance Criteria:**
- [ ] 文本模式接受直接粘贴的非空 JD 内容
- [ ] 文件模式接受 PDF、DOCX、TXT 和 Markdown 文件，并对不支持的类型给出明确错误
- [ ] 链接模式只接受公开的 HTTP/HTTPS 地址
- [ ] 文件和网页内容被转换为纯文本后再调用 JD Extractor
- [ ] 系统抽取岗位名称、公司、地点、职级、岗位职责、必备技能和加分技能；无法确定的字段保留为空，不得编造
- [ ] 每项技能尽可能保留对应的原文 evidence
- [ ] 有效输入识别成功后自动保存，JD 状态变为 `ready`
- [ ] 抽取或 LLM 识别失败时状态变为 `failed`，且可从失败步骤重试
- [ ] 后端单测覆盖三种来源、无效输入、抽取失败和重试路径

### US-003: 查看和筛选 JD 列表

**Description:** As a user, I want to scan and filter my saved JDs so that I can quickly find a target role.

**Acceptance Criteria:**
- [ ] 顶部主导航在截图标注区域增加“JD 列表”和“计划列表”入口
- [ ] `/jobs` 页面展示岗位名称、公司、来源、职级、处理状态和更新时间
- [ ] 列表支持按岗位或公司关键词搜索
- [ ] 列表支持按录入来源和处理状态筛选
- [ ] 默认按最近更新时间倒序排列
- [ ] 页面分别提供空、加载、成功和加载失败状态
- [ ] 中英文文案、前端 typecheck 和浏览器验证通过

### US-004: 创建 JD 的前端流程

**Description:** As a user, I want one clear creation flow for all supported sources so that I can add a JD without learning separate pages.

**Acceptance Criteria:**
- [ ] JD 列表页提供明确的“添加 JD”命令按钮
- [ ] 创建界面使用分段控件切换“粘贴文本 / 上传文件 / 网页链接”模式
- [ ] 当前模式缺少有效输入时提交按钮不可用
- [ ] 提交后列表立即显示新记录及“识别中”状态
- [ ] 成功后可进入详情页，失败后原输入不丢失并显示重试入口
- [ ] 重复链接或相同内容指纹再次提交时给出疑似重复提示，但允许用户确认后继续保存
- [ ] 中英文文案、前端 typecheck 和浏览器验证通过

### US-005: 查看并编辑结构化结果

**Description:** As a user, I want to inspect and correct extracted JD fields so that downstream matching and planning use accurate data.

**Acceptance Criteria:**
- [ ] 详情页同时提供原文和结构化结果视图
- [ ] 用户可以修改岗位名称、公司、地点、职级、职责、必备技能和加分技能
- [ ] 保存后刷新页面仍显示修改结果
- [ ] 人工修改后的记录标记对应字段或整体结果为 `manual`
- [ ] 取消编辑不会写入任何更改
- [ ] 保存失败时保留尚未提交的编辑内容并显示可重试提示
- [ ] 前端 typecheck 和浏览器验证通过

### US-006: 重试、重新识别和删除 JD

**Description:** As a user, I want to recover failed records and remove obsolete ones so that the library stays usable.

**Acceptance Criteria:**
- [ ] `failed` 记录提供重试操作，并从失败的抽取或识别步骤重新执行
- [ ] `ready` 记录提供重新识别操作
- [ ] 重新识别前明确提示 AI 结果可能被覆盖
- [ ] 删除前显示确认对话框，取消时不产生删除请求
- [ ] 被计划引用的 JD 不得被直接删除，接口返回引用冲突并引导用户先处理关联计划
- [ ] 后端单测、前端 typecheck 和浏览器验证通过

### US-007: 将 JD 用于下游流程

**Description:** As a user, I want to reuse a ready JD for matching and planning so that I do not need to paste it again.

**Acceptance Criteria:**
- [ ] `ready` 状态的 JD 详情提供“匹配简历”和“创建计划”入口
- [ ] 进入匹配流程时传递已有 `jd_id`，不创建重复 JD
- [ ] 进入计划流程时预选当前 `jd_id`
- [ ] 非 `ready` 状态不显示可执行的下游操作，并说明需要先完成识别
- [ ] 集成测试覆盖已有 JD 进入匹配和计划创建的路径
- [ ] 浏览器验证通过

## 4. Functional Requirements

- FR-1: 系统必须提供 JD 列表、详情、创建、更新、删除、重试和重新识别接口。
- FR-2: 系统必须支持粘贴文本作为 JD 输入。
- FR-3: 系统必须支持从 PDF、DOCX、TXT 和 Markdown 文件提取 JD 文本。
- FR-4: 系统必须支持从公开 HTTP/HTTPS 网页提取 JD 文本。
- FR-5: 网页抓取必须阻止 localhost、环回地址、私网地址和非 HTTP/HTTPS 协议。
- FR-6: 网页抓取必须限制连接超时、响应大小、重定向次数和允许的内容类型。
- FR-7: 系统必须保存 JD 的原始内容和录入来源元数据。
- FR-8: 系统必须记录 JD 的 `processing`、`ready` 或 `failed` 状态。
- FR-9: 系统必须调用现有 JD Extractor 生成结构化字段。
- FR-10: 系统必须将无法从原文确定的字段保存为空值，而不是生成推测内容。
- FR-11: LLM 识别成功后系统必须自动持久化结构化结果。
- FR-12: LLM 识别失败后系统必须保留原始输入和失败原因。
- FR-13: 用户必须能够编辑并保存结构化结果。
- FR-14: 系统必须记录结构化结果的 LLM 或人工来源。
- FR-15: 列表接口必须支持关键词、来源、状态筛选和更新时间排序。
- FR-16: 系统必须对疑似重复的来源链接或内容指纹给出提示。
- FR-17: 系统必须允许用户确认后保存疑似重复的 JD。
- FR-18: 系统必须允许 `ready` JD 通过 `jd_id` 进入现有简历匹配流程。
- FR-19: 系统必须允许 `ready` JD 通过 `jd_id` 进入计划创建流程。
- FR-20: 系统不得直接删除仍被计划引用的 JD。

## 5. Non-Goals

- 不支持需要登录、验证码或绕过反爬限制的招聘页面。
- 不支持批量导入 JD。
- 不支持招聘网站的持续同步或岗位变更监控。
- 不支持 JD 对外分享或多人协作。
- 不在本功能中重写 JD Matching 算法。

## 6. Design Considerations

- 在截图标注的顶部导航空白区域加入“JD 列表”和“计划列表”，保持现有导航密度。
- 延续当前 Neo-brutalism 视觉、黑色边框与硬阴影，不新增独立视觉体系。
- 创建入口使用命令按钮；录入来源使用分段控件；处理状态使用统一状态标记。
- 详情页优先保证原文与结构化结果可对照检查，不将核心字段隐藏在多层弹窗内。
- 删除、重新识别等不可逆或覆盖操作必须使用确认对话框。

## 7. Technical Considerations

- 扩展现有 `JobDescriptionModel`、`backend/api/v1/jd.py` 和 `JDExtractor`，不新增重复 JD 聚合。
- 文件文本提取应复用已有简历解析器中适用的 PDF、DOCX、TXT 和 Markdown 能力。
- 网页抓取必须在后端执行，并落实 SSRF、大小、超时、重定向和内容类型限制。
- 原文与结构化字段分开存储；人工修正不得覆盖原始来源内容。
- 列表数据必须由后端持久化提供，不采用仅 localStorage 的历史记录方案。
- 现有 `POST /api/v1/jd` 的调用方应保持兼容。

## 8. Success Metrics

- 文本、文件和公开网页三种来源都能完成“提交 -> 识别 -> 查看 -> 编辑”流程。
- 任一处理失败状态都展示具体失败阶段，并提供有效重试入口。
- 用户无需重新粘贴原文即可将已有 JD 用于简历匹配或创建计划。
- 用户可以从 JD 列表在两次页面跳转内打开任一 ready JD 的详情。
- 所有新增后端测试、前端 typecheck、lint 和浏览器验收通过。

## 9. Open Questions

- JD 文件大小是否直接沿用简历上传限制，还是设置更小的独立限制？
- MVP 是否需要保存网页抓取时的 HTML 快照，还是只保存转换后的文本和来源 URL？

