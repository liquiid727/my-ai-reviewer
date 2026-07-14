# PRD: MVP 面试问答流程

## Introduction

在简历上传/解析/评估流程已完成的基础上，补全 Phase 1 MVP 的核心功能——**面试问答流程**。候选人上传简历后，系统根据简历解析结果和岗位 JD 由 LLM 动态生成 5 道面试题目，采用**逐题问答**的交互模式（类似聊天式面试），每题回答后**实时 LLM 评分**并给出反馈，支持**最多 2 轮追问**以深入考察，全部作答完成后生成结构化面试报告。

跑通此流程后，系统将实现完整闭环：

```
上传简历 → 解析/评估 → 创建面试 → 生成题目 → 逐题问答(含追问) → 实时评分 → 面试报告
```

---

## Goals

- 实现从简历到面试报告的完整闭环，跑通 MVP 验收标准
- 支持逐题问答交互模式，每题实时 LLM 评分并反馈
- 支持每题最多 2 轮动态追问，根据回答质量自动决定是否追问
- 题目覆盖多个考察维度（基础/项目/架构/行为），由 LLM 根据简历和 JD 动态生成
- 面试结束后生成结构化报告，包含综合评分、各维度评分、优劣势和改进建议
- 所有面试数据持久化到 PostgreSQL，支持历史查询

---

## User Stories

### US-001: 创建面试会话

**Description:** As a 面试官/候选人, I want to 基于已解析的简历创建一场面试会话 so that 系统可以根据简历内容准备面试题目。

**Acceptance Criteria:**
- [ ] 提供 `POST /api/v1/interview/create` 接口，接收 `resume_id`（必填）和 `jd_text`（选填）和 `question_count`（默认 5，范围 3-10）
- [ ] 校验 resume_id 对应的简历已处理完成（status 为 evaluated 或 classified），否则返回 400 错误
- [ ] 创建 Interview 记录（status=pending），存储关联的 resume_id 和 jd_text
- [ ] 返回 interview_id 和 status
- [ ] 数据库新增 interviews 表，包含 id, resume_id, jd_text, status, question_count, created_at, updated_at 等字段
- [ ] Typecheck/lint passes

### US-002: 生成面试题目

**Description:** As a 系统, I want to 根据简历解析结果和 JD 自动生成面试题目 so that 题目与候选人背景高度相关。

**Acceptance Criteria:**
- [ ] 提供 `POST /api/v1/interview/{id}/start` 接口，触发题目生成并返回第一题
- [ ] 调用 LLM 生成指定数量的题目，每题包含：question_text, stage(basic/project/architecture/behavior), difficulty(easy/medium/hard), expected_points(参考答案要点)
- [ ] 题目生成优先匹配 JD 要求（岗位所需技能、职责、技术栈），其次结合简历中的具体经历进行个性化定制
- [ ] 如果提供了 JD，至少 60% 的题目直接对应 JD 中的核心要求
- [ ] 生成的题目持久化到 interview_questions 表
- [ ] Interview status 从 pending 变为 in_progress
- [ ] 响应返回第一题的 question_id、question_text、stage、当前题号(1/N)
- [ ] Typecheck/lint passes

### US-003: 逐题提交回答与实时评分

**Description:** As a 候选人, I want to 逐题提交我的回答并立即看到评分反馈 so that 我知道自己的表现如何。

**Acceptance Criteria:**
- [ ] 提供 `POST /api/v1/interview/{id}/answer` 接口，接收 question_id 和 answer_text
- [ ] 校验该 question_id 属于当前面试且尚未回答
- [ ] 调用 LLM 对回答进行评分，返回：score(0-100), feedback(评语), key_points_hit(命中的要点), key_points_missed(遗漏的要点)
- [ ] 评分结果持久化到 question_answers 表
- [ ] 响应包含评分结果 + is_followup(是否需要追问) + next 信息（下一题或追问或结束）
- [ ] 如果是最后一题且无追问，返回 is_finished=true
- [ ] 空回答或过短回答（<10 字符）返回 400 错误提示
- [ ] Typecheck/lint passes

### US-004: 动态追问（Follow-up）

**Description:** As a 系统, I want to 在候选人回答模糊或过于简短时自动生成追问 so that 能更深入地考察候选人的真实水平。

**Acceptance Criteria:**
- [ ] 每题最多追问 2 轮，追问计数存储在 question_answers 表
- [ ] LLM 评分时同时判断是否需要追问（score < 70 或回答缺少关键要点时触发）
- [ ] 追问由 LLM 根据原题和候选人回答动态生成，不是固定模板
- [ ] 追问题目通过 answer 接口的响应中 `followup_question` 字段返回
- [ ] 候选人对追问的回答通过同一 answer 接口提交，question_id 不变，附加 is_followup=true
- [ ] 追问的评分会更新该题的最终评分，权重由 LLM 根据追问回答质量动态分配（如追问回答优秀则提高追问权重，回答差则降低）
- [ ] 达到最大追问轮次或回答质量达标后，自动进入下一题
- [ ] Typecheck/lint passes

### US-005: 生成面试报告

**Description:** As a 面试官, I want to 在面试结束后获取结构化的面试报告 so that 我可以综合评估候选人表现并做出录用决策。

**Acceptance Criteria:**
- [ ] 最后一题完成后自动触发报告生成（异步，Celery task）
- [ ] 提供 `GET /api/v1/interview/{id}/report` 接口获取报告
- [ ] 报告包含：overall_score, dimension_scores(技术能力/项目深度/系统设计/沟通表达/问题解决), per_question_summary, strengths, weaknesses, recommendation(strong_yes/yes/maybe/no/strong_no), summary
- [ ] 报告由 LLM 综合所有问答记录和评分生成，不是简单的分数平均
- [ ] 报告持久化到 interview_reports 表
- [ ] Interview status 变为 completed
- [ ] 如果报告尚未生成完成，接口返回 status=generating 提示稍后重试
- [ ] Typecheck/lint passes

### US-006: 面试问答前端页面

**Description:** As a 候选人, I want to 在浏览器中进行面试问答 so that 我有一个清晰的界面来回答问题和查看反馈。

**Acceptance Criteria:**
- [ ] 新增 InterviewPage 页面（路由 `/interview/:id`），采用聊天式 UI 布局
- [ ] 顶部显示面试进度条（当前第 N 题 / 共 M 题）
- [ ] 每题显示：题目文本、所属阶段标签（basic/project/architecture/behavior）、难度标签
- [ ] 底部文本输入区域，支持多行输入，Enter 提交（Shift+Enter 换行）
- [ ] 提交后显示 loading 状态，收到评分后展示：分数、评语、命中/遗漏要点
- [ ] 追问以追加消息的形式展示在同一题的对话流中
- [ ] 面试结束后显示"查看面试报告"按钮，跳转到报告页面
- [ ] 沿用项目 Neobrutalism 设计风格
- [ ] Typecheck/lint passes
- [ ] Verify in browser using dev-browser skill

### US-007: 面试报告前端页面

**Description:** As a 面试官, I want to 在浏览器中查看结构化的面试报告 so that 我可以直观地了解候选人的综合表现。

**Acceptance Criteria:**
- [ ] 新增 InterviewReportPage 页面（路由 `/interview/:id/report`）
- [ ] 顶部显示综合评分仪表盘（复用已有的 ScoreGauge 组件）和录用建议标签
- [ ] 雷达图展示 5 个维度评分（复用已有的 Recharts 雷达图模式）
- [ ] 逐题回顾区域：每题折叠展示题目、回答、评分、评语（含追问记录）
- [ ] 优势/不足区域，卡片式布局
- [ ] AI 总结评语区域
- [ ] 沿用项目 Neobrutalism 设计风格
- [ ] Typecheck/lint passes
- [ ] Verify in browser using dev-browser skill

### US-008: 面试列表与入口

**Description:** As a 用户, I want to 查看已创建的面试列表和从简历详情页发起面试 so that 我可以管理多次面试。

**Acceptance Criteria:**
- [ ] 在 ResumePage 底部增加"开始面试"按钮（在已有的"View AI Evaluation Report"按钮旁边）
- [ ] 点击后弹出对话框，输入 JD 文本（选填）和题目数量（默认 5），确认后创建面试并跳转
- [ ] 提供 `GET /api/v1/interview/list` 接口，支持按 resume_id 筛选，返回面试列表
- [ ] 新增 InterviewListPage 页面（路由 `/interviews`），展示面试列表卡片（显示创建时间、状态、综合评分）
- [ ] 侧边导航栏新增"Interviews"入口
- [ ] Typecheck/lint passes
- [ ] Verify in browser using dev-browser skill

---

## Functional Requirements

- FR-1: 系统 must 提供创建面试会话的 API，关联已解析的简历和可选的 JD 文本
- FR-2: 系统 must 调用 LLM 根据 JD 和简历解析结果动态生成指定数量的面试题目，优先匹配 JD 要求，其次结合简历内容
- FR-3: 系统 must 将生成的题目按阶段（basic/project/architecture/behavior）合理分布，题目侧重 JD 所需技能的考察
- FR-4: 系统 must 支持逐题问答模式，每次只返回当前题目，回答后才返回下一题
- FR-5: 系统 must 在候选人提交回答后调用 LLM 实时评分，返回分数、评语和要点分析
- FR-6: 系统 must 根据回答质量自动判断是否需要追问，每题最多追问 2 轮
- FR-7: 系统 must 对追问题目由 LLM 根据原题和已有回答动态生成
- FR-8: 系统 must 在所有题目完成后异步生成结构化面试报告
- FR-9: 系统 must 将面试报告持久化，包含综合评分、维度评分、优劣势和录用建议
- FR-10: 系统 must 提供面试列表查询 API，支持按简历 ID 筛选
- FR-11: 系统 must 在前端提供聊天式面试交互界面，含进度指示和实时反馈
- FR-12: 系统 must 在前端提供面试报告展示页面，含评分可视化和逐题回顾

---

## Non-Goals (Out of Scope)

- **不做 RAG 题库检索**：题目完全由 LLM 生成，不从预设题库中召回（Phase 3）
- **不做多阶段路由**：不区分 Resume/Basic/Project/System Design/Behavior 等阶段的动态路由（Phase 2 Workflow 升级）
- **不做语音/视频面试**：仅支持文字输入（Phase 7 Multimodal）
- **不做代码题执行**：不支持在线编程和代码运行验证（Phase 6 Sandbox）
- **不做多租户/权限控制**：不区分面试官和候选人角色（Phase 8 SaaS 化）
- **不做 WebSocket 实时推送**：评分通过 HTTP 响应同步返回，不做 WS 推送
- **不做面试中途暂停/恢复**：MVP 阶段面试需一次性完成，数据已持久化但不提供恢复入口（可作为后续迭代）
- **不做 JD 解析**：JD 作为纯文本输入，不做结构化解析

---

## Design Considerations

- **聊天式 UI**：面试页面采用类似即时通讯的消息流布局，系统问题在左侧，候选人回答在右侧，评分反馈以卡片形式插入对话流中
- **复用已有组件**：ScoreGauge、Badge、Card、Progress、Accordion 等 Neobrutalism 风格组件均可直接复用
- **报告页面**：复用 EvaluationPage 的雷达图和评分布局模式，保持视觉一致性
- **进度指示**：顶部固定进度条，显示「第 2 题 / 共 5 题」和当前阶段标签

---

## Technical Considerations

- **LLM Gateway 复用**：面试出题、评分、追问判断、报告生成均通过已有的 LLMGateway 调用，无需新增 Provider
- **Celery 异步**：报告生成通过 Celery task 异步执行，与现有的简历处理流水线模式保持一致
- **Agent 目录**：后端 `agents/` 已预留 question_agent、followup_agent、evaluation_agent、report_agent，需实现具体逻辑
- **LangGraph 编排**：后端 `workflow/` 已预留 graphs/ 和 nodes/，MVP 直接使用 LangGraph 编排面试流程（analyze_resume → generate_questions → [LOOP: present_question → evaluate_answer → decide_followup] → generate_report），为 Phase 2 的多阶段路由和动态追问升级打好基础
- **数据库新增 3 张表**：interviews、interview_questions、interview_reports（question_answers 可嵌入 interview_questions 的 JSONB 字段，或独立建表）
- **评分动态加权**：追问评分与首轮评分加权合并，权重由 LLM 根据追问回答质量动态分配（评分时 LLM 同时输出 weight 字段）
- **Prompt 工程**：需为出题、评分、追问判断、报告生成分别设计 system prompt，放在 `infrastructure/llm/prompts/` 下

---

## Success Metrics

- 创建面试到生成第一题的延迟 < 15 秒（LLM 调用时间）
- 单题评分响应延迟 < 10 秒
- 面试报告生成延迟 < 30 秒
- 面试全流程（5 题无追问）可在 10 分钟内完成
- 所有面试数据（题目、回答、评分、报告）100% 持久化，重启不丢失

---

## Open Questions

> 以下问题已在 review 中确认：
>
> 1. ~~追问评分权重~~ → **已确认**：由 LLM 根据追问回答质量动态分配权重，不使用固定比例
> 2. ~~面试暂停/恢复~~ → **已确认**：MVP 不支持，后续迭代再考虑
> 3. ~~JD 文本的影响权重~~ → **已确认**：题目优先匹配 JD 要求，JD 是第一优先级，简历内容是第二优先级
> 4. ~~LangGraph 引入时机~~ → **已确认**：MVP 直接使用 LangGraph 编排面试流程

暂无新的 Open Questions。
