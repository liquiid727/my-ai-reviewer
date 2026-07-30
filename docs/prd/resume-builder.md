Resume Builder（简历制作与美化平台）

一、项目背景（Background）

`tasks/prd-parser.md` 定义了 Resume Intelligence Platform 的大方向：解析 → 拆解 → Facts → Profile → 评估 → 面试 → 匹配。

在这条数据底座之上，候选人侧还需要一个"正向"的能力：不仅能读懂一份简历，还能帮助候选人**制作出一份更好的简历**，并为后续面试做准备。

因此本 PRD 定义 Resume Builder 子系统，覆盖：

简历制作
简历解析复用（依托 RIP-001 / RIP-002）
AI 润色
图片（证件照）美化
面试应对准备（下一阶段）
面试知识库（下一阶段，对接 AIP-003）

二、项目目标（Goals）

围绕"一份可交付的简历"建设完整闭环：

上传旧简历 → 解析拆解 → 生成结构化草稿 → 编辑 / 润色 / 美化 → 打分 → 导出 PDF

最终形成：

ParsedResume / CandidateProfile
↓
ResumeDraft（结构化草稿）
↓
编辑 + AI 润色 + 照片美化
↓
模板渲染（HTML → PDF，自动一页）
↓
评分与改进建议
↓
导出交付

三、核心能力（Core Capabilities）

3.1 简历草稿（ResumeDraft）——已实现

- 从已解析简历的 CandidateProfile 一键生成草稿（`POST /resume-builder/from-resume/{resume_id}`）
- 草稿结构：identity（姓名/联系方式/链接）+ summary + sections（工作/项目/教育/技能/证书）
- 条目级编辑：heading / subheading / date_range / bullets
- 区块可隐藏（visible）、可排序（order）

3.2 模板与排版 ——已实现

- 内置模板：classic（经典单栏）、modern（现代双栏）、compact（紧凑）
- DesignTokens：字体、主题色、页边距、排版密度
- 密度四档（loose / normal / tight / compact），自动一页时逐档收缩
- PDF 导出：Playwright(chromium) 打印 A4，超出一页返回 overflow 提示；可持久化到 MinIO

3.3 AI 润色（Polish）——已实现

- 按区块提交原始 bullets，LLM 返回润色建议（保留原文，逐条接受）
- 支持传入目标岗位上下文
- 失败降级：LLM 不可用时返回明确错误，不破坏草稿

3.4 简历评分（Score）——已实现

- 基于草稿整体内容由 LLM 打分并给出改进建议

3.5 图片（证件照）美化 ——本期新增

目标：候选人上传任意生活照/自拍，产出符合简历规范的证件照。

能力：

- 照片上传：JPG / PNG，限制大小（≤10MB）
- 人像裁剪：自动检测人脸区域，裁剪为标准一寸比例（295×413）
- 背景替换：抠除原背景，替换为白 / 蓝 / 红纯色
- 画质增强：亮度、对比度、锐化基础增强
- 结果预览：原图与处理结果对照，用户确认后写入草稿
- 模板渲染：三套模板均支持头像占位（无照片时布局不留白）

约束：

- 处理必须本地完成（Pillow + rembg），照片不发送第三方服务
- 原图与处理结果均存 MinIO，可追溯、可重新处理
- 处理失败（无人脸 / 抠图失败）时给出明确原因，允许用户直接使用原图

四、用户流程（User Flow）

1. 上传旧简历（或从空白开始）
2. 系统解析并生成草稿
3. 编辑内容，对区块逐条润色
4. 上传照片 → 选择背景色 → 预览 → 确认
5. 选择模板与密度，预览
6. 打分，按建议迭代
7. 导出 PDF

状态覆盖要求（每个用户可见流程必须覆盖）：

- Empty：无草稿 / 无照片时的引导态
- Loading：解析中 / 润色中 / 照片处理中 / 导出中
- Success：结果预览与确认
- Failure：明确错误原因 + 可重试入口

五、下一阶段（Next Phase）

5.1 面试应对准备（Interview Prep）

基于 ResumeDraft + CandidateProfile 生成：

- 自我介绍脚本（30s / 2min 两个版本）
- 简历中可能被追问的点与应答建议
- 弱项 / 风险点的应对话术
- 目标岗位（JD）导向的准备清单（依托 RIP-003 匹配结果）

5.2 面试知识库（Interview Knowledge Base）

对接 roadmap Phase 3（AIP-003 RAG 知识库）：

- 题库数据源：Go / Redis / MySQL / Kubernetes / System Design 等
- 按候选人技能画像检索个性化练习题
- 沉淀高频问题与参考答案，供面试 Agent（AIP-001/002）与备考复用

六、非目标（Non-Goals）

- 不做在线协作编辑
- 不做付费模板市场
- 照片美化不做美颜级别的人脸修饰（仅证件照规范化）
- 面试知识库的内容生产工具（另行规划）

七、追溯（Traceability）

- 数据底座：`tasks/prd-parser.md`（RIP-001 / RIP-002）
- JD 匹配：`specs/RIP-003-jd-matching/`
- 本期实现规格：`specs/RIP-004-resume-builder/spec.md`
- 面试知识库：`specs/roadmap.md` Phase 3（AIP-003）
