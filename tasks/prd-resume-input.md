# PRD: Resume Input Pipeline（简历输入管道）

## Introduction/Overview

简历输入管道是 AI Interview Platform 的基础数据处理模块，覆盖从简历文件上传到 AI 评估的完整流程。

当前简历解析市场停留在"提取 JSON"阶段，缺乏统一数据模型、事实追溯能力和 AI 分析能力。本模块的目标是建设一套完整的 Resume Intelligence Pipeline，为后续 JD 匹配、Interview Agent、人才画像等 AI 能力提供统一的数据底座。

**核心流程：**
```
Upload → Detect Type → Extract Text → LLM Parse (Sections + Facts + Profile) → Classify → AI Evaluate
```

**范围：** 后端 API + 前端页面（上传、解析结果展示、评分报告）

---

## Goals

- 支持 PDF / DOCX / TXT / Markdown 四种格式的简历上传与存储（MinIO）
- 使用 LLM 对简历进行结构化信息抽取，所有抽取结果附带 Evidence（原文、置信度、页码、段落）
- 构建标准化 CandidateProfile（身份、教育、工作、项目、技能、证书）
- 自动生成简历分类标签（技术方向、经验等级、行业领域）
- AI 多维度评估：综合评分 + 各维度评分 + 优势分析 + 风险分析 + 面试建议
- 异步任务管理：长耗时的解析 + 评估流程通过 Celery 异步执行，前端轮询状态
- 前端提供完整的上传→查看→评估交互体验
- 前端提供 LLM 配置入口，用户可选择/填入 API Key、模型和服务商（支持 OpenAI、Claude、DeepSeek 等）

---

## User Stories

### US-001: 项目基础设施搭建
**Description:** As a developer, I need the project skeleton and infrastructure so that subsequent features have a runnable foundation.

**Acceptance Criteria:**
- [ ] FastAPI 项目初始化，目录结构符合 `design/coding-guidelines.md` 的 DDD 分层
- [ ] SQLAlchemy 2.x async + Alembic 迁移配置完成
- [ ] 创建数据库表：`users`、`resumes`、`files`，字段符合 `design/database.md`
- [ ] `resumes` 表增加 `resume_evaluations` JSON 字段（存储 AI 评估结果），`status` 字段使用已有枚举 `ResumeStatus`
- [ ] 新增 `resume_evaluations` 表：`id`, `resume_id`, `overall_score`, `dimension_scores`(JSON), `strengths`(JSON), `risks`(JSON), `interview_suggestions`(JSON), `summary`, `llm_model`, `created_at`
- [ ] Docker Compose 配置：PostgreSQL 16 + Redis 7 + MinIO
- [ ] MinIO bucket `resumes` 创建，连接配置通过环境变量注入
- [ ] Celery + Redis broker 配置完成，Worker 可启动
- [ ] 健康检查端点 `GET /api/health` 返回 `{"status": "ok"}`
- [ ] Typecheck (mypy/pyright) 通过

### US-002: 简历文件上传
**Description:** As a user, I want to upload my resume file so that the system can process and analyze it.

**Acceptance Criteria:**
- [ ] `POST /api/v1/resume/upload` 接收 multipart/form-data 文件
- [ ] 支持文件格式校验：`.pdf`, `.docx`, `.txt`, `.md`，拒绝其他格式返回 `code: 1001`
- [ ] 文件大小限制 10MB，超限返回 `code: 1001`
- [ ] 文件上传至 MinIO `resumes` bucket，路径格式：`{user_id}/{uuid}.{ext}`
- [ ] 计算文件 SHA256 hash，存入 `files` 表
- [ ] 创建 `resumes` 记录，状态设为 `uploaded`
- [ ] 响应格式符合 API 规范：`{"code": 0, "message": "success", "data": {"resume_id": "...", "file_id": "...", "status": "uploaded"}}`
- [ ] 相同 hash 文件重复上传时，返回已有 resume_id 而非重复创建
- [ ] Typecheck 通过

### US-003: 简历文本提取
**Description:** As a system, I need to extract raw text from uploaded resume files so that downstream LLM parsing can work on structured text.

**Acceptance Criteria:**
- [ ] PDF 解析使用 PyMuPDF，提取全部页面文本，保留段落结构
- [ ] DOCX 解析使用 python-docx，提取段落和表格内容
- [ ] TXT / Markdown 直接读取原始文本
- [ ] 提取结果保存到 `resumes.raw_text` 字段
- [ ] 记录页数信息到 `files` 表
- [ ] 解析成功后更新 `resumes.status` 为 `text_parsed`
- [ ] 解析失败时更新状态为 `failed`，记录错误信息到 `resumes.parse_error`
- [ ] 文本提取服务作为独立 domain service，不依赖 API 层
- [ ] Typecheck 通过

### US-004: LLM 结构化信息抽取
**Description:** As a system, I need to use LLM to extract structured information from resume text, with evidence tracing for every extracted fact.

**Acceptance Criteria:**
- [ ] 调用 LLM（Claude/GPT）对 raw_text 进行结构化抽取
- [ ] 输出包含：Section 分割结果（按 `ResumeSectionType` 枚举分类）
- [ ] 输出包含：ResumeFact 列表，每个 Fact 包含 `fact_type`、`key`、`value`、`evidence`（source_text, confidence, page, section）
- [ ] 输出包含：CandidateProfile（identity, education, work_experiences, projects, skills, certificates）
- [ ] 所有抽取结果必须附带 Evidence，禁止仅输出最终 JSON
- [ ] LLM 输出使用 Structured Output / JSON Mode 强制格式
- [ ] 抽取结果保存到 `resumes.parsed_result`（JSON 字段）
- [ ] 状态更新为 `fact_extracted`
- [ ] LLM 调用记录 token_usage 和 model 信息
- [ ] 复用 `backend/domain/resume/schemas.py` 中已有的 Pydantic 模型
- [ ] Typecheck 通过

### US-005: 简历自动分类
**Description:** As a system, I need to automatically classify resumes with tags so that recruiters can quickly filter and understand candidate profiles.

**Acceptance Criteria:**
- [ ] 根据 CandidateProfile 生成分类标签，覆盖：技术方向（Backend/Frontend/AI/DevOps 等）、行业领域（Finance/E-commerce/Cloud 等）、经验等级（Junior/Mid/Senior/Staff）
- [ ] 计算统计信息：工作年限、项目数量、技术深度、行业覆盖、管理经验
- [ ] 标签存入 `CandidateProfile.ability_tags`
- [ ] 状态更新为 `classified`
- [ ] 分类逻辑可基于规则或 LLM（推荐规则优先，降低成本）
- [ ] Typecheck 通过

### US-006: AI 简历多维度评估
**Description:** As a recruiter, I want an AI-powered multi-dimensional evaluation of the resume so that I can quickly assess candidate quality and know what to ask in interviews.

**Acceptance Criteria:**
- [ ] 调用 LLM 基于 CandidateProfile 进行评估，模拟技术面试官视角
- [ ] 综合评分：Overall Score (0-100)
- [ ] 维度评分（每项 0-100 + reason + evidence）：技术能力、项目质量、工程能力、架构能力、业务复杂度、影响力、成长性、AI 能力
- [ ] 优势分析：列出候选人核心优势（3-5 条），每条附带依据
- [ ] 风险分析：列出潜在风险（简历空档、职责疑似夸大、技术跨度异常等），每条附带依据
- [ ] 面试建议：值得追问的问题、可能存在夸大的地方、建议验证的方向、建议跳过的方向
- [ ] 综合评价：生成 2-3 句话的 Summary（如"适合高级后端岗位，偏工程型，分布式经验较好"）
- [ ] 评估结果存入 `resume_evaluations` 表
- [ ] LLM 调用记录 model、token_usage、cost
- [ ] Typecheck 通过

### US-007: 异步解析管道
**Description:** As a system, I need to orchestrate the parse→extract→classify→evaluate pipeline as async tasks so that the user doesn't wait for long-running LLM calls.

**Acceptance Criteria:**
- [ ] 文件上传后自动触发 Celery 异步任务链：text_extract → llm_parse → classify → evaluate
- [ ] `GET /api/v1/resume/{resume_id}/status` 返回当前处理状态和进度
- [ ] 任一步骤失败时，状态标记为 `failed`，记录失败步骤和错误信息，不阻塞已完成步骤的结果查看
- [ ] `GET /api/v1/resume/{resume_id}` 返回当前已完成的解析结果（即使后续步骤仍在进行）
- [ ] 支持手动重试失败步骤：`POST /api/v1/resume/{resume_id}/retry`
- [ ] 任务超时设置：文本提取 30s，LLM 抽取 120s，评估 120s
- [ ] Typecheck 通过

### US-008: 前端 - 项目初始化 + 简历上传页面
**Description:** As a user, I want a clean upload interface to submit my resume file and see the upload progress.

**Acceptance Criteria:**
- [ ] React + Vite + TypeScript 项目初始化
- [ ] 集成 Tailwind CSS + Neobrutalism UI 组件库（https://www.neobrutalism.dev/docs）
- [ ] 集成 Zustand 状态管理
- [ ] 集成 React Router 路由
- [ ] 上传页面路由：`/upload`
- [ ] 支持拖拽上传和点击选择文件
- [ ] 显示文件格式提示（支持 PDF / DOCX / TXT / MD，最大 10MB）
- [ ] 上传进度条展示
- [ ] 上传成功后显示"解析中"状态，自动轮询 `/api/v1/resume/{id}/status`
- [ ] 解析完成后自动跳转到解析结果页
- [ ] 文件格式错误或超限时显示友好错误提示
- [ ] 整体 UI 风格遵循 Neobrutalism 设计语言（粗边框、鲜明配色、硬阴影）
- [ ] Typecheck (tsc) 通过
- [ ] 在浏览器中验证完整上传流程

### US-009: 前端 - 解析结果展示页
**Description:** As a user, I want to see the parsed resume data in a structured, readable format so that I can verify the extraction quality.

**Acceptance Criteria:**
- [ ] 页面路由：`/resume/{id}`
- [ ] 展示候选人基本信息卡片（姓名、联系方式、链接）
- [ ] 分 Tab 或分区展示：教育背景、工作经历、项目经历、技能列表、证书
- [ ] 每项抽取结果旁显示置信度指示器（高/中/低）
- [ ] 可展开查看原文 Evidence（source_text + page）
- [ ] 显示自动分类标签（ability_tags）
- [ ] 加载中状态：部分数据未就绪时显示 skeleton loading
- [ ] Typecheck 通过
- [ ] 在浏览器中验证页面展示效果

### US-010: 前端 - 评估报告页
**Description:** As a recruiter, I want to see the AI evaluation report with scores, analysis, and interview suggestions in an intuitive layout.

**Acceptance Criteria:**
- [ ] 页面路由：`/resume/{id}/evaluation`（或嵌入结果页的 Tab）
- [ ] 综合评分醒目展示（大数字 + 环形进度条或仪表盘）
- [ ] 各维度评分以雷达图或横向条形图展示
- [ ] 优势列表（绿色标识）和风险列表（红色/黄色标识）分栏展示
- [ ] 面试建议区域：追问问题列表、疑似夸大项、验证方向
- [ ] Summary 文本突出展示
- [ ] 当评估仍在进行时显示"评估中"动画
- [ ] Typecheck 通过
- [ ] 在浏览器中验证报告展示效果

### US-011: 后端 - LLM 配置管理 API
**Description:** As a system, I need to store and retrieve user's LLM provider settings so that resume parsing and evaluation use the user-configured model.

**Acceptance Criteria:**
- [ ] 新增 `llm_configs` 表：`id`, `user_id`, `provider`(enum), `api_key`(encrypted), `model_name`, `base_url`(optional), `is_active`(bool), `created_at`, `updated_at`
- [ ] `POST /api/v1/settings/llm` 保存 LLM 配置（provider, api_key, model_name, base_url）
- [ ] `GET /api/v1/settings/llm` 获取当前 LLM 配置（api_key 脱敏返回，只显示最后 4 位）
- [ ] `PUT /api/v1/settings/llm/{id}` 更新已有配置
- [ ] `DELETE /api/v1/settings/llm/{id}` 删除配置
- [ ] 支持的 Provider 枚举：`openai`, `anthropic`, `deepseek`, `custom`（自定义 OpenAI 兼容端点）
- [ ] API Key 在数据库中加密存储（AES 或 Fernet）
- [ ] 保存前验证 API Key 有效性（调用目标 provider 的 models 列表 API 测试连通性）
- [ ] 解析/评估时优先使用用户配置的 LLM，未配置则使用系统默认
- [ ] Typecheck 通过

### US-012: 前端 - LLM 模型配置页面
**Description:** As a user, I want to configure my LLM API settings through the frontend so that I can choose which AI model to use for resume analysis.

**Acceptance Criteria:**
- [ ] 页面右上角或导航栏显示"设置"图标按钮，点击进入配置页面或弹出配置 Modal
- [ ] 配置页面路由：`/settings`（或 Modal 形式）
- [ ] Provider 下拉选择：OpenAI / Claude (Anthropic) / DeepSeek / 自定义（Custom）
- [ ] 根据选中的 Provider 动态显示对应的模型列表：
  - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, o3-mini 等
  - Claude: claude-sonnet-4-20250514, claude-haiku-4-5-20251001, claude-opus-4-20250514 等
  - DeepSeek: deepseek-chat, deepseek-reasoner 等
  - Custom: 用户手动填写 model name
- [ ] API Key 输入框（密码类型，可切换显示/隐藏）
- [ ] Base URL 输入框（仅 Custom provider 时必填，其他 provider 可选用于代理）
- [ ] "测试连接" 按钮：调用后端验证 API Key 有效性，显示成功/失败状态
- [ ] 保存成功后显示 Toast 提示
- [ ] 未配置 LLM 时，上传页面显示引导提示"请先配置 AI 模型"
- [ ] Typecheck 通过
- [ ] 在浏览器中验证配置流程：选择 Provider → 填写 Key → 测试连接 → 保存

---

## Functional Requirements

- FR-1: 系统必须接受 PDF / DOCX / TXT / Markdown 格式的简历文件上传，单文件最大 10MB
- FR-2: 系统必须将上传文件存储到 MinIO 对象存储，并计算文件 hash 防重复
- FR-3: 系统必须使用 PyMuPDF (PDF) 和 python-docx (DOCX) 提取简历原始文本
- FR-4: 系统必须调用 LLM 对简历文本进行结构化抽取，输出符合 CandidateProfile schema
- FR-5: 系统必须为每个抽取事实保存 Evidence（原文引用、置信度、页码、所属段落）
- FR-6: 系统必须根据 Profile 自动生成分类标签（技术方向、经验等级、行业领域）
- FR-7: 系统必须调用 LLM 对简历进行多维度评估，输出评分 + 优势 + 风险 + 面试建议
- FR-8: 系统必须通过 Celery 异步执行解析和评估管道，提供状态查询 API
- FR-9: 系统必须提供 RESTful API，响应格式统一为 `{"code": 0, "message": "...", "data": {...}}`
- FR-10: 前端必须提供上传、结果查看、评估报告三个核心页面
- FR-11: 系统必须支持用户配置 LLM Provider（OpenAI / Anthropic / DeepSeek / Custom），API Key 加密存储
- FR-12: 前端必须提供 LLM 配置入口，支持 Provider 选择、API Key 填写、模型选择、连接测试

---

## Non-Goals (Out of Scope)

- **不包含** JD 匹配功能（属于下一阶段 JD Matching）
- **不包含** Interview Agent 面试流程（属于 AIP-001 后续开发）
- **不包含** 用户认证/权限系统（第一版使用硬编码 user_id 或匿名用户）
- **不包含** OCR 图片解析、LinkedIn/Boss 等平台导入
- **不包含** 简历版本管理（同一候选人多份简历对比）
- **不包含** 多语言简历支持（第一版聚焦中英文）
- **不包含** RAG 问题库检索
- **不包含** 语音/视频输入

---

## Design Considerations

### UI/UX
- **设计系统:** 采用 Neobrutalism UI（https://www.neobrutalism.dev/docs），特征为粗边框、鲜明配色、硬阴影、直角/微圆角
- 上传页面采用简洁的拖拽上传设计，使用 Neobrutalism 的 Card + Button 组件
- 解析结果页采用卡片式布局，分区展示不同信息维度
- 评估报告页以数据可视化为核心（雷达图、进度条、标签云）
- 整体风格：Neobrutalism 风格 — 大胆、直观、高信息密度

### 现有组件复用
- 复用 `backend/domain/resume/schemas.py` 中已有 Pydantic 模型（CandidateProfile, ResumeFact, Evidence 等）
- 复用 `backend/domain/resume/enums.py` 中已有枚举（ResumeStatus, ResumeSectionType, FactType）
- 遵循 `design/api-guidelines.md` 的 API 规范
- 遵循 `design/coding-guidelines.md` 的 DDD 分层和编码规范
- 遵循 `design/database.md` 的数据库设计（resumes、files 表结构）

---

## Technical Considerations

- **LLM 接口:** 统一使用 OpenAI 兼容格式（openai SDK），Anthropic 通过其官方 SDK 或兼容层接入。LLM Gateway 抽象层根据用户配置的 provider 路由到对应 SDK
- **Structured Output:** LLM 抽取使用 JSON Mode / Tool Use 确保输出格式可控
- **数据库迁移:** 使用 Alembic 管理 schema 变更
- **异步任务:** Celery 任务链处理长耗时操作，Redis 作为 broker
- **文件存储:** MinIO S3 兼容存储，通过 presigned URL 或代理下载
- **数据模型:** `resumes` 表设计为独立实体（移除 interview_id 外键），简历可独立于面试存在，后续通过 `interviews.resume_id` 关联
- **Note:** `backend/domain/resume/schemas.py` 存在 typo（`Opional` → `Optional`，`from enum import enum` → `from enum import Enum`），实现时需修复
- **前端技术栈:** React + Vite + TypeScript + Tailwind CSS + Zustand + React Router + Neobrutalism UI
- **Parser Version:** 每次解析记录 parser_version，便于未来重新解析

---

## Success Metrics

- 用户可以在 30 秒内完成简历上传
- PDF/DOCX 文本提取成功率 ≥ 95%
- LLM 结构化抽取准确率 ≥ 85%（通过人工抽样验证）
- 完整管道（上传→评估）耗时 ≤ 60 秒
- 评估报告包含至少 5 个维度评分 + 3 条优势 + 3 条风险分析
- 前端页面加载时间 ≤ 2 秒

---

## Open Questions

1. 评估维度的权重是否可配置？还是先固定为等权重？
2. 前端是否需要暗色模式支持？
