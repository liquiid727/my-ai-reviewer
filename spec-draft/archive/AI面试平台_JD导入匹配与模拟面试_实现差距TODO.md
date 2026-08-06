# AI 面试平台 PRD 实现差距与 TODO 清单

> 对照文档：`docs/prd/AI面试平台_JD导入匹配与模拟面试_PRD.md`

> 审计日期：2026-08-05

> 审计范围：主工作树当前代码、迁移、前端入口、Spec/Issue、测试与交付状态。

> 说明：本清单是差距审计，不代表本次已经完成任何代码交付。当前工作树有大量既有未提交改动，本清单只新增本文件。

## 1. 结论

当前 PRD 描述的是一条完整产品链路：

```text
JD 导入与资料库
  -> 简历/JD 匹配
  -> 面试场景
  -> Interview Plan
  -> 面试运行状态机
  -> 动态追问与单题评分
  -> 面试报告
  -> 学习与求职行动
```

现有 RIP-010、RIP-011、RIP-012 只覆盖其中三个增量：图片 JD 导入、证据约束的 v2 匹配、匹配结果向 Plan/Interview 的消费。它们没有覆盖 PRD 中完整的面试场景、Interview Plan、面试运行状态机、覆盖矩阵和最终报告契约。因此，当前主要问题不是单个功能漏写，而是 PRD 的产品范围大于已经拆出的 Spec 范围。

主工作树目前可以确认的状态如下：

| 能力 | 当前判断 | 证据与说明 |
| --- | --- | --- |
| 文本、文件、URL JD 导入 | 已有旧链路 | `backend/api/v1/jd.py:65-124`、`backend/application/jd_service/processing.py:160-202`；不能据此证明 PRD 的手动创建、完整来源字段和版本管理全部完成。 |
| 图片 JD 后端链路 | 部分实现 | 当前已有 `POST /jd/import/images`、图片校验、MinIO 资产、Vision processing 和 Celery 链路，见 `backend/api/v1/jd.py:126-157`、`backend/application/jd_import_service.py:286-360`、`backend/application/jd_service/processing.py:73-139`；RIP-010 任务和浏览器验收仍未关闭。 |
| `hybrid_v2` 匹配后端 | 部分实现 | 当前已有 domain、application service、Celery task、迁移和 create/detail/recompute/list 路由，见 `backend/api/v1/jd.py:231-310`、`backend/application/jd_matching/service.py:99-350`；前端仍调用旧 `/jd/match`。 |
| 匹配结果和证据 UI | 未接入 | `frontend/src/api/jd.ts:85-90` 仍只调用旧同步接口，`frontend/src/pages/JDDetailPage.tsx:156-204` 没有 v2 状态、维度、硬条件和证据面板。 |
| Plan 消费匹配结果 | 部分实现 | Plan 已保存 `match_result_id` 和输入快照，见 `backend/application/plan_service.py:294-354`；但 freshness 仍由旧 `get_fresh_match()` 的时间比较和 `JDMatchingService` 驱动，见 `backend/application/plan_service.py:61-92`。 |
| Interview 消费匹配结果 | 未接入 | 数据模型已有 `jd_id`、`match_result_id`、snapshot 字段，见 `backend/infrastructure/db/models.py:211-234`；创建 API/service 仍只有 `jd_text`，见 `backend/api/v1/interview.py:26-37`、`backend/application/interview_service.py:47-83`。 |
| 旧文字面试 | 已有 MVP 路径 | LangGraph 已有出题、回答评估、最多两轮追问和报告任务，见 `backend/workflow/graphs/interview_graph.py:24-47`、`backend/workflow/nodes/decide_next.py:18-87`、`backend/tasks/interview_tasks.py:49-107`；它不是 PRD 所要求的结构化 JD/匹配驱动面试。 |
| PRD 面试场景、Plan、运行事件和完整报告 | 未完成 | 当前 API/模型没有对应的完整结构化契约；前端面试 API 只有 create/start/answer/status/report，见 `frontend/src/api/interview.ts:12-74`。 |
| RIP-010~012 交付状态 | 未验收 | 三个 `tasks.md` 仍为 `Proposed` 且 issue 均为未勾选；`specs/RIP-010-jd-vision-import/spec.md:243-249`、`specs/RIP-011-evidence-bound-jd-matching/spec.md:271-278`、`specs/RIP-012-jd-matching-consumption/spec.md:188-194` 都要求真实测试和浏览器证据。 |

因此当前不能把这份 PRD 标记为「已完成」。更准确的结论是：旧 MVP 可运行，JD Intelligence v2 已有后端骨架，但完整用户闭环和交付证据仍缺失。

## 2. 状态口径

- `已实现（旧路径）`：代码和既有测试已有能力，但只满足旧 Spec/旧契约，不能自动升级为本 PRD 已完成。
- `部分实现`：代码、迁移或 API 已存在，但上下游未接入，或缺少失败、并发、隐私、浏览器和真实运行证据。
- `未实现`：没有可被用户或下游服务调用的完整契约和运行路径。
- `待决策`：PRD、Spec、实现之间的产品语义不一致，必须先统一口径，不能直接写成开发 TODO。
- `未验证`：代码看起来存在，但没有当前版本的自动化、迁移、集成或浏览器证据。

## 3. P0 TODO：先恢复端到端闭环

### TODO-P0-01：建立 PRD -> Spec -> Issue -> Code -> Test 全量追踪矩阵

- 状态：`未完成`。
- 差距：当前 `spec-draft/jd-intelligence-v2-2026-08-05.md` 只覆盖 FR-1~FR-30；没有把 PRD 第 22 节验收标准、面试运行阶段、报告内容和后续行动逐项映射到既有 Spec 或新 Spec。
- 根因：把「JD Intelligence v2 增量」当成了整份产品 PRD 的实现拆分，导致需求范围在 `spec-draft` 处被缩小但没有记录排除项。
- 前置条件：确认本期 PRD 是否覆盖完整的模拟面试，还是只交付 JD Intelligence v2；如果是前者，需要补齐面试相关 Spec；如果是后者，需要在 PRD 或版本说明中明确本期边界。
- 执行内容：生成一张按 PRD 章节/验收项编号的矩阵，列出 `已覆盖 / 部分覆盖 / 未覆盖 / 非本期`，每项绑定 Spec、Issue、代码入口、测试和证据文件。
- 验收证据：矩阵中 PRD `22.1~22.5`、`10~14`、`17~20` 均有唯一归属；未完成项不能只写「后续处理」。
- 关联：PRD `:2182-2229`；issue #092 `tasks/issues/issue-092-jd-intelligence-drift-baseline.md:7-16`；RIP-012 `spec.md:98-100`。

### TODO-P0-02：完成图片 JD 导入的前端可达性和恢复闭环

- 状态：`后端部分实现，前端未接入，验收未验证`。
- 差距：主工作树已有图片后端入口和 Vision pipeline，但前端来源类型仍是 `text | file | url`，导入对话框也只有三种 Tab，见 `frontend/src/types/jd.ts:3-5`、`frontend/src/components/jd/JDImportDialog.tsx:104-111`。
- 根因：RIP-010 的 application/backend slice 已进入工作树，RIP-010 issue #096/#097 的 UI、失败、重试和浏览器 closeout 没有完成。
- 前置条件：确认 `POST /api/v1/jd/import/images` 的 multipart 字段、错误码、processing 状态和 Vision capability 响应是稳定契约；不要让前端依赖未类型化字段。
- 执行内容：增加多图选择、顺序预览、1~8 张和 10MB/30MB 提示、MIME/损坏文件校验、外部 Vision 披露确认；接入 processing/ready/failed/retry/expired 状态和单定时器轮询；ready 后进入可编辑详情页。
- 验收证据：后端 API/worker/迁移测试；合成图片成功、超限、伪造 MIME、损坏、Vision 失败、重试、删除和 stale worker 场景；桌面和移动浏览器截图/结果；日志无 base64、完整转写、prompt 和 key。
- 关联：PRD `:82-307`、`:2184-2192`；RIP-010 `spec.md:34-42, 63-143, 231-249`；issue #094~#097。

### TODO-P0-03：把 `hybrid_v2` 匹配接入结果 UI和用户入口

- 状态：`后端 API 骨架存在，前端仍是旧路径`。
- 差距：后端已有 `/jd/matches` create/detail/recompute/list，见 `backend/api/v1/jd.py:231-310`；前端 `matchJobDescription()` 仍调用旧 `POST /jd/match`，返回类型也只有 `{ id: string }`，见 `frontend/src/api/jd.ts:85-90`。JD 详情页成功后只 toast，不展示结果，见 `frontend/src/pages/JDDetailPage.tsx:156-204`。
- 根因：RIP-011 的 contract/service 已写入，但 RIP-012 的 typed frontend consumption 未实现；旧 `rules_v1` 兼容路径和新 `hybrid_v2` 主路径没有在 UI 中分层。
- 前置条件：用 Pydantic request/response schema 固定 create/detail/history/recompute 契约，明确旧 `/jd/match` 只保持 `rules_v1` 兼容，不再作为新 UI 默认入口。
- 执行内容：扩展前端类型，展示 queued/running/ready/failed/stale/recompute pending；分开展示 hard filter、nullable 总分、七维分数、证据、coverage/confidence、风险、缺口、recommendation、版本和人工确认；防止活动 run 重复提交。
- 验收证据：API 合同测试、旧接口回归、空/加载/失败/重试/stale/recompute 组件测试；JD 详情桌面/移动浏览器成功和失败场景；确认不展示原始简历正文。
- 关联：PRD `:533-789`、`:1644-1679`、`:2194-2201`；RIP-011 `spec.md:179-256`；RIP-012 `spec.md:67-80, 123-127`；issue #101~#103。

### TODO-P0-04：让 Plan 只消费 fingerprint-fresh 的 `hybrid_v2`

- 状态：`部分实现`。
- 差距：Plan 已落库 `match_result_id` 和快照，但 `get_fresh_match()` 仍按时间比较，并在缺失/过期时调用旧 `JDMatchingService().match()`，见 `backend/application/plan_service.py:61-92`；这不能保证 matcher/policy/prompt/schema/provider/model 或 Resume Facts 变化被识别。
- 根因：RIP-008 原有 freshness 逻辑没有替换为 RIP-011 的共享 fingerprint policy；新增模型字段先于消费者迁移完成。
- 前置条件：先完成 TODO-P0-03 的 v2 create/detail 契约，并定义 Plan 生成失败/超时/重新计算时的明确错误和用户动作。
- 执行内容：复用 `backend/application/jd_matching/freshness.py`；创建和 regenerate 只复用 ready 且 fingerprint 一致的 v2 结果；缺失/stale 时调用 v2 application service；快照保存 match id、mode、fingerprint、版本及最小证据；不能静默使用旧结果。
- 验收证据：JD revision、Profile/Facts revision、matcher/policy/prompt/schema/model 变化矩阵；v2 重算成功/失败/超时、late worker、regenerate 原子性和旧 Plan API 回归测试。
- 关联：PRD `:1010-1113`、`:2005-2045`；RIP-008 `spec.md:366-415`；RIP-012 `spec.md:83-90, 129-143`；issue #104。

### TODO-P0-05：把 JD/match context 接入 Interview 创建、提问和报告

- 状态：`模型字段存在，运行时未接入`。
- 差距：`InterviewModel` 已有 `jd_id`、`match_result_id`、JD/match snapshot 字段，但创建请求只有 `jd_text`，见 `backend/api/v1/interview.py:26-37`、`backend/application/interview_service.py:47-83`；报告任务也只把 `jd_text` 和问答传给 Report Agent，见 `backend/tasks/interview_tasks.py:49-101`。
- 根因：issue #105 只被拆出，没有完成跨 API、持久化、隐私和 prompt 的联调；当前面试仍是「自由文本 JD + 简历」路径。
- 前置条件：匹配结果必须是同一 JD/Resume、`ready` 且 fresh；Resume Facts/Profile 必须使用已批准的脱敏数据；明确旧 `jd_text` 兼容行为。
- 执行内容：创建请求支持 `jd_id`、可选 `match_result_id`，保留旧路径；校验跨资源、failed/stale、缺失 JD；写入最小不可变 context snapshot/fingerprint；提问和报告只接收 bounded JD/match evidence；保留 draft/resume 二选一约束。
- 验收证据：jd_text-only、jd_id-only、fresh match、stale/cross-resource/failed match、snapshot immutable、PrivacyGuard、旧客户端回归和报告内容测试。
- 关联：PRD `:798-1207`、`:1512-1586`、`:1690-1758`、`:2203-2229`；RIP-012 `spec.md:91-96, 145-163`；issue #105。

### TODO-P0-06：完成一次可复现的全链路 closeout

- 状态：`未验证`。
- 差距：当前有迁移文件并且 `alembic heads` 指向 `p6d7e8f9a0b1`，但没有 RIP-010~012 当前版本的迁移 round-trip、Celery、LLM spy、API、前端和浏览器结果；三个 `tasks.md` 仍全部未勾选。
- 根因：实现文件和交付证据没有同步推进；代码存在被误当成 issue 完成。
- 前置条件：P0-02~P0-05 的契约稳定；准备不含真实 PII 的合成图片 JD、脱敏 Resume Facts/Profile、mock LLM/provider 和独立 PostgreSQL/Redis/MinIO。
- 执行内容：执行 image -> ready JD -> v2 match -> result UI -> stale/recompute -> Plan -> Interview -> report；验证重复请求、失败重试、删除和 late worker；同步 tasks、roadmap、current、design 和 tests/results。
- 验收证据：每一步有 `spec_id`、`run_id`、命令、状态、日志/截图引用；未运行写 `NOT_RUN`，环境阻塞写 `BLOCKED`，不把静态检查替代浏览器验收。
- 关联：issue #097、#102、#106；RIP-010~012 各自 `Definition of Done`。

## 4. P1 TODO：补齐产品契约和运行时可靠性

### TODO-P1-01：解决匹配评分契约冲突：8 维还是 7 维

- 状态：`待决策`。
- 差距：PRD 写的是 8 个维度（包括基础条件、优先项/加分项），见 `PRD:572-587`；JD Intelligence v2 的 `DIMENSION_WEIGHTS` 和 issue #099 固定为 7 个维度，见 `backend/domain/jd/matching_v2.py:156-164`、`tasks/issues/issue-099-rip011-hard-filter-policy.md:7-18`。
- 根因：新 Spec 为了区分 hard filter 与 soft score 调整了评分模型，但没有回写 PRD 的 MVP 口径。
- 前置条件：产品确认 8 维是本期硬验收，还是新版 v2 的 7 维 + 独立硬条件模型。
- 执行内容：确定唯一权重表、总分计算、UI 展示和历史结果兼容策略；同步 PRD、spec-draft、RIP-011、API 类型、测试 fixture。
- 验收证据：边界分数、缺失维度、coverage、recommendation 和旧 `rules_v1` 回归测试。

### TODO-P1-02：解决 Embedding 和硬条件「封顶」语义冲突

- 状态：`待决策`。
- 差距：PRD 要求规则 + 技能标准化 + Embedding + LLM 证据判断，并描述缺失技能/年限不足的分数封顶，见 `PRD:589-684`；RIP-011 只实现 deterministic hard filter + LLM evidence，缺少 Embedding provider/index/fallback 契约，并将 hard fail/unknown 转为人工复核，见 `specs/RIP-011-evidence-bound-jd-matching/spec.md:58-120`。
- 根因：产品评分策略在 PRD 和新 policy 之间发生了行为变化，但没有明确废弃旧语义。
- 前置条件：确认 Embedding 是否属于 MVP；确认 hard fail 是否影响总分、只影响 recommendation，还是两者都影响。
- 执行内容：若 Embedding 不进 MVP，明确写入 Non-goal；若进入 MVP，新增 provider、索引、超时和降级 issue；统一 hard filter policy 和 UI 文案。
- 验收证据：pass/fail/unknown、证据不足、学历/地点/证书/年限、封顶或人工确认的完整决策表和测试。

### TODO-P1-03：补齐 v2 fingerprint、重试、并发和 fallback 语义

- 状态：`部分实现，有明确风险`。
- 差距：共享 fingerprint 结构预留了 `resume_facts_revision`，见 `backend/application/jd_matching/freshness.py:37-58`，但 v2 service 调用 `current_match_fingerprint()` 时没有传入 facts revision，见 `backend/application/jd_matching/service.py:117-178`；匹配服务先查再插入，唯一约束冲突也没有回读已有 run，见 `backend/application/jd_matching/service.py:118-158`。
- 另一个风险：`run_match()` 创建 LLM matcher 失败时静默降级为 `HeuristicJDMatcher`，见 `backend/application/jd_matching/service.py:188-194`。这可能把 provider/config 故障伪装成可用匹配结果。
- 前置条件：明确 Facts/Profile 的 revision 来源；决定 fallback 是否只允许测试或显式 `rules_v1` 模式。
- 执行内容：传入真实 facts revision；捕获唯一约束并回读 active/ready；区分确定性输入错误、timeout/429、schema correction 和 provider error；增加指数退避、attempt/failure code；配置或 LLM matcher 失败时 fail closed。
- 验收证据：重复请求、并发插入、force/recompute、late worker、timeout/429、schema 一次修正、fallback 禁止和隐私 spy 测试。
- 关联：RIP-010 `spec.md:133-139`；RIP-011 `spec.md:146-153`；issue #097、#100~#102。

### TODO-P1-04：补齐结构化 Interview Scenario 与 Interview Plan

- 状态：`未实现`。
- 差距：PRD 要求场景是结构化配置，创建后先生成并确认 Interview Plan，计划包含阶段、问题、能力项、风险验证和 rubric，见 `PRD:790-1113`；当前实现直接由 LangGraph 生成问题，状态只保存 `question_count`、questions 和 follow-up，见 `backend/workflow/state.py:32-51`。
- 根因：AIP-001 的 MVP 文字面试先实现了「简历 + 自由文本 JD -> 问题」，新 PRD 没有对应的 Scenario/Plan Spec 和数据契约。
- 前置条件：完成 P0-01，确定场景模板、版本、阶段、问题来源和用户确认步骤。
- 执行内容：新增 scenario/version、plan/stage/question 契约；支持综合模拟、技术一面、项目深挖等 MVP 场景；创建与开始分离；Plan 生成必须可审计和可重试。
- 验收证据：创建页配置、计划预览/确认、取消/失败/重新生成、版本快照和完整 API/浏览器流程。

### TODO-P1-05：补齐 Interview Session 状态、事件和操作

- 状态：`部分实现`。
- 差距：旧图支持回答、追问和结束，但 PRD 要求准备、开场、阶段切换、暂停、恢复、跳过、提前结束、覆盖矩阵和 `interview_events`，见 `PRD:1115-1455`、`:1888-1935`；当前前端 API 只有 create/start/answer/status/report，见 `frontend/src/api/interview.ts:21-74`。
- 根因：当前状态机以 LangGraph interrupt 为中心，没有将产品要求的 session/question/event 生命周期持久化为稳定业务契约。
- 前置条件：P1-04 的 plan/scenario 已稳定；确定暂停恢复的所有权、过期和并发提交规则。
- 执行内容：扩展 session/question/answer/evaluation/event 表和 API；记录 stage/question/follow-up/score/report 事件；提供 pause/resume/skip/complete/cancel；覆盖矩阵成为内部状态而非仅 prompt 文本。
- 验收证据：重复提交、断点恢复、并发回答、无限追问上限、时间预算、跳过/结束、事件回放和失败重试测试。

### TODO-P1-06：补齐面试报告的 JD 覆盖和行动建议

- 状态：`基础报告已有，PRD 报告未完成`。
- 差距：现有 Report Agent 能生成总分、维度、逐题摘要、优缺点和 recommendation，见 `backend/tasks/interview_tasks.py:92-107`；PRD 还要求高表现/薄弱问题、JD 覆盖、岗位适配、学习计划和下一次专项面试建议，见 `PRD:1512-1586`、`:2222-2229`。
- 根因：报告输入目前没有匹配维度、证据、覆盖矩阵和结构化行动对象，前端也只展示旧报告字段。
- 前置条件：P0-05 的 match context 和 P1-05 的 coverage/evaluation 数据可用。
- 执行内容：定义 report schema；让报告区分回答表现与岗位适配；展示已验证/风险/未验证能力；行动建议绑定学习计划、简历优化或专项面试入口；增加报告生成幂等、重试和安全错误。
- 验收证据：报告与单题评分一致性、JD 覆盖率、缺口分类、失败重试、重复生成和桌面/移动端展示。

### TODO-P1-07：补齐 PRD 的 JD 字段和导入方式范围

- 状态：`部分实现`。
- 差距：PRD 本期列出文本、文件、图片、公开链接、手动创建，以及来源平台、薪资、备注、标签、业务上下文等字段，见 `PRD:82-122`、`:310-402`；当前 `JDStructuredPatch` 和 `JDExtraction` 主要覆盖 title/company/location/seniority/responsibilities/skills，见 `backend/domain/jd/schemas.py:63-127`。
- 根因：RIP-010 以现有 RIP-007 JD schema 为前提，只补图片输入，没有将整份 PRD 的字段模型纳入本轮。
- 前置条件：确认这些字段是否是当前 MVP 的硬验收；如果不是，明确标为非本期并保留后续 Spec 入口。
- 执行内容：统一 source/version/field provenance/evidence 数据结构；必要时补 manual endpoint、薪资/标签/业务上下文字段和版本操作；不重复创建第二套 JD schema。
- 验收证据：手动创建、编辑、重新解析、字段保护、版本历史、重复检测和旧导入回归。

### TODO-P1-08：补齐匹配报告后的用户行动

- 状态：`未进入当前 Spec`。
- 差距：PRD 要求从报告触发简历优化、针对性简历、学习计划、求职计划和专项面试；当前 RIP-012 只定义 Plan 和 Interview 的匹配消费，未定义其他行动的契约，见 `PRD:751-759`、`specs/RIP-012-jd-matching-consumption/spec.md:75-96`。
- 前置条件：先确认这些行动是否属于本期 MVP；不要因为已有 Builder/Plan 页面就默认它们已完成 PRD 行动闭环。
- 执行内容：按已有模块分别建立入口和输入快照；未确认的行动标记为 future scope，不混入 P0 closeout。
- 验收证据：从匹配报告进入目标动作，并携带正确 JD/Resume/Match 版本和最小证据。

## 5. P2 TODO：质量、评测和持续交付

### TODO-P2-01：建立 RIP-010~012 专属测试计划和结果目录

- 状态：`未建立`。
- 差距：仓库已有 RIP-007/RIP-008 测试计划和结果，但当前未发现 RIP-010~012 的专属 `tests/plans`、`tests/results` 和浏览器场景；Spec 仍要求这些证据。
- 执行内容：按 US/FR 建立 unit/API/integration/migration/privacy/concurrency/frontend/browser matrix；结果必须带 `spec_id`、`run_id`、命令和状态。
- 验收证据：每个 P0 TODO 至少有正常、空、失败、重试、过期/并发和隐私分支；NOT_RUN/BLOCKED 保持原状态。

### TODO-P2-02：补齐 JD/匹配/面试可观测性和 Agent Eval

- 状态：`未进入 RIP-010~012`。
- 差距：PRD 列出导入/解析/匹配/计划/面试/报告成功率、耗时、完成率、追问次数、成本和幻觉/死循环指标，见 `PRD:2005-2112`；当前新增 Spec 主要要求元数据和测试，没有运行时指标契约。
- 前置条件：先完成事件模型（P1-05）和隐私字段白名单。
- 执行内容：定义事件、指标、trace/request/run 关联、标签和聚合周期；禁止记录原文、base64、prompt 和 API key；增加 JD 解析、匹配、面试评测 fixture。
- 验收证据：合成数据下的指标样例、模型/Prompt 版本对比、稳定性和成本报告。

### TODO-P2-03：完成交互质量和浏览器可访问性验收

- 状态：`未验证`。
- 差距：已有页面有一部分 loading/empty/failure/轮询，但没有新匹配证据面板、图片导入和面试完整流程的桌面/移动证据；当前已有 `git diff --check` 失败，问题位于既有改动 `frontend/src/components/ui/alert.tsx:14` 的 trailing whitespace。
- 执行内容：完成新流程的窄屏布局、键盘操作、图标按钮 accessible name、轮询在终态/失焦/卸载/超时停止、失败后重试；单独清理或由代码变更负责人处理已有 whitespace，不要把它混入本 TODO 的文档提交。
- 验收证据：前端 lint/build/component test、桌面/移动截图和关键交互结果；全库 `git diff --check` 只有在既有问题处理后才能宣称通过。

### TODO-P2-04：同步 as-built 状态和版本边界

- 状态：`未完成`。
- 差距：`current/project-status.md` 仍指向 RIP-001/#038，`specs/roadmap.md` 和 `specs/issues/README.md` 仍把 RIP-010~012 标为 `Proposed`；而主工作树已出现相关代码和迁移。这会让后续 Agent 把旧状态当成当前真相。
- 执行内容：每个 issue 完成后同步 `tasks.md`、roadmap、issue index、current、design/database/backend/frontend 文档；把「代码存在」「本地验收」「已发布」分开记录。
- 验收证据：状态文件中的每个 `shipped/in-review` 都有对应 commit、测试结果和浏览器/部署证据；未发布的脏工作树不写成 shipped。

## 6. 明确排除的误报

以下内容不应直接作为当前 TODO 的开发缺口：

1. **不要重复列「后端图片 API 不存在」**。主工作树当前已有 `/jd/import/images` 和对应 processing/service 代码；真正缺的是前端可达性、契约测试和端到端验收。
2. **不要把 `rules_v1` 旧匹配当成错误**。保留旧 `POST /jd/match` 是兼容要求；缺口是新用户流程没有默认进入 `hybrid_v2`，且两种模式的 UI/状态没有分开。
3. **不要说旧面试完全不存在**。现有 AIP-001 路径已经有文字出题、回答评估、两轮追问和基础报告；缺的是结构化场景、Plan、JD/match evidence、事件和完整报告，不是从零重写所有面试代码。
4. **不要把语音、视频、数字人、群面当成当前 MVP 阻塞项**。PRD 已将它们列入 P1/P2；先完成文字模式的可追溯闭环。
5. **不要把迁移文件存在或 `alembic heads` 有输出当成迁移通过**。必须执行实际 upgrade/downgrade/重放，并保留结果。
6. **不要把旧 RIP-007/RIP-008 的历史 PASS 直接套用到 RIP-010~012**。新代码、schema、前端和迁移需要重新运行当前版本的验证。

## 7. 推荐执行顺序

```text
P0-01 范围与追踪矩阵
  -> P1-01/P1-02 产品评分决策
  -> P0-02 图片导入 UI + acceptance
  -> P0-03 hybrid_v2 UI + typed contract
  -> P0-04 Plan fresh consumer
  -> P0-05 Interview match context
  -> P1-04 Scenario + Interview Plan
  -> P1-05 Session/event state machine
  -> P1-06 Report contract
  -> P0-06 full closeout
  -> P2-01~P2-04 quality and status closeout
```

如果本期目标只是交付 `JD Intelligence v2`，可以先执行 P0-01 并把 P1-04~P1-06 标成下一版本；如果目标是完成当前 PRD，则 P1-04~P1-06 不能继续留在「未归属」状态。
