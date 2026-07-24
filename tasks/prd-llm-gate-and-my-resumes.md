# PRD: LLM 配置门禁 + 我的简历（本地列表）

## Introduction/Overview

本 PRD 针对简历上传体验的两个增强需求，作为 [prd-resume-input.md](./prd-resume-input.md) 的补充规格，独立成文，不改动原 PRD。

**问题背景：**

1. **LLM 未配置也能上传，注定失败。** 当前上传页仅有一条软文字提示（"请先配置 AI 模型"），未配置 LLM 时用户依然可以上传简历，后续解析/评估管道必然失败，用户体验割裂、排错成本高。同时，用户在界面上看不清 LLM 到底"配没配好"——右上角齿轮只是一个静态图标，缺乏状态反馈与引导。
2. **上传过的简历无处回看。** 用户上传简历后没有一个"历史列表"入口，无法回看或重新选择之前传过的简历，每次都要重新走上传流程。

**目标概述：**

- 在 LLM 未"配置完成"（配置存在且测试通过）前，**硬拦截**上传动作并弹窗引导用户去设置页配置与测试。
- 右上角齿轮增设**明确的配置状态指示**，重点突出引导用户点击去配置。
- 新增**"我的简历"**界面，基于浏览器 localStorage 保存上传过的简历列表，用户可回看、选择、删除，并可随时点击"上传新简历"。

**范围：** 前端为主（拦截、状态可视化、我的简历页、i18n）；后端仅新增 LLM 配置的"已验证"状态字段以支撑门禁判定。

---

## Goals

- 未"配置完成"LLM 时，点击上传/选择文件立即被拦截并弹窗引导，杜绝无效上传。
- 定义并落地"配置完成"的明确判定：存在 `is_active=true` 且 `verified=true` 的 LLM 配置。
- 右上角齿轮呈现三态状态徽标（未配置 / 已配置未验证 / 已验证），未就绪时醒目引导用户点击配置。
- 新增"我的简历"页面，基于 localStorage 展示历史上传列表，支持查看、选择、删除本地记录、再次上传。
- 全部新增文案覆盖中英文（i18n）。

---

## User Stories

### Feature A — LLM 配置门禁与状态可视化

#### US-A1: 后端 - LLM 配置"已验证"状态

**Description:** As a system, I need to persist whether an LLM config has passed a connection test so that the frontend can enforce a hard gate on resume upload.

**Acceptance Criteria:**
- [ ] `llm_configs` 表新增字段：`verified`(bool, 默认 false) 与 `last_verified_at`(datetime, 可空)
- [ ] Alembic 迁移脚本创建，向后兼容（已有配置默认 `verified=false`）
- [ ] `POST /api/v1/settings/llm/test` 测试通过后，若请求携带已保存的 `config_id`，将对应配置的 `verified` 置为 `true` 并更新 `last_verified_at`；测试失败置为 `false`
- [ ] `_serialize`（`backend/api/v1/settings.py`）在响应中返回 `verified` 与 `last_verified_at`
- [ ] 定义"配置完成"= 存在 `is_active=true` 且 `verified=true` 的配置
- [ ] 当已保存配置的 `api_key` / `provider` / `model_name` / `base_url` 被更新（`PUT /settings/llm/{id}`）时，`verified` 重置为 `false`（配置变更需重新测试）
- [ ] `verified` 一旦置为 true 不设过期：仅在配置关键字段变更或测试失败时才失效
- [ ] Typecheck 通过

#### US-A2: 前端 - 配置就绪状态判定

**Description:** As a frontend, I need a single source of truth for "LLM ready" so that both the gate and the gear indicator stay consistent.

**Acceptance Criteria:**
- [ ] `frontend/src/types/settings.ts` 的 `LLMConfig` 增加 `verified: boolean` 与 `last_verified_at: string | null` 字段
- [ ] 复用 `GET /api/v1/settings/llm`（`frontend/src/api/settings.ts`）拉取配置列表，就绪判定 = 列表中存在 `is_active === true && verified === true` 的配置
- [ ] 就绪状态集中管理（如 `settingsStore` 或统一 hook），供上传拦截与齿轮指示复用，避免逻辑重复
- [ ] Typecheck (tsc) 通过

#### US-A3: 前端 - 上传硬拦截 + 弹窗引导

**Description:** As a user without a verified LLM config, I want to be clearly stopped and guided when I try to upload so that I don't waste an upload that will surely fail.

**Acceptance Criteria:**
- [ ] 进入上传页时若 LLM 未就绪，上传区域禁用（拖拽/点击选择均不触发上传）
- [ ] 用户点击上传/选择文件时，立即弹出提示 Modal，说明"需先配置并测试 AI 模型后才能上传简历"
- [ ] Modal 提供主操作按钮"去配置"，点击跳转 `/settings`；提供次要"取消"关闭
- [ ] 拦截覆盖三种未就绪态：无任何配置、有配置但未测试（`verified=false`）、测试失败
- [ ] 就绪后（存在 active+verified 配置）上传区域恢复可用，正常走原有上传流程
- [ ] 原有软文字提示（`upload.tip`）保留或升级为更醒目的引导，且与门禁状态一致
- [ ] Typecheck 通过
- [ ] 在浏览器中验证：无配置 → 被拦截 → 去配置并测试通过 → 回到上传页可正常上传

#### US-A4: 前端 - 齿轮状态指示与引导

**Description:** As a user, I want the top-right gear to clearly show whether my LLM is configured so that I know when I need to take action.

**Acceptance Criteria:**
- [ ] 导航栏齿轮按钮（`frontend/src/components/Layout.tsx`）叠加状态徽标，呈现三态：
  - 未配置（无 active 配置）：红色/警示徽标 + 脉冲动画，强引导点击
  - 已配置未验证（有 active 但 `verified=false`）：黄色警示徽标
  - 已验证（active + verified）：绿色对勾徽标
- [ ] 未就绪时提供明显的引导（如齿轮旁文字/角标或 hover 提示"点击配置 AI 模型"）
- [ ] 徽标状态与 US-A2 就绪判定实时一致（配置变更/测试后更新）
- [ ] 视觉风格遵循 Neobrutalism（粗边框、鲜明配色、硬阴影）
- [ ] Typecheck 通过
- [ ] 在浏览器中验证三态显示

#### US-A5: 前端 - 设置页"测试即验证"

**Description:** As a user, I want testing a saved config to mark it verified so that I can immediately start uploading.

**Acceptance Criteria:**
- [ ] `SettingsPage` 对已保存配置点击"测试连接"成功后，触发后端标记该配置 `verified=true`
- [ ] 测试成功 Toast 提示明确指向下一步（如"已验证，可以开始上传简历"）
- [ ] 测试失败时该配置保持/回退为 `verified=false`，Toast 说明失败原因
- [ ] 配置列表 UI 展示每条配置的验证状态（已验证/未验证标签）
- [ ] Typecheck 通过
- [ ] 在浏览器中验证：保存配置 → 测试通过 → 齿轮变绿 → 上传解锁

### Feature B — 我的简历（本地 localStorage 列表）

#### US-B1: 前端 - 上传成功写入本地历史

**Description:** As a user, I want my uploaded resumes to be remembered in the browser so that I can find them later.

**Acceptance Criteria:**
- [ ] 上传成功后（`UploadPage` 拿到 `resume_id` 时），将该简历记录写入 localStorage
- [ ] 记录字段包含：`resume_id`、`file_name`、`uploaded_at`(ISO 时间)、`status`(最新已知状态)
- [ ] 轮询状态更新时同步刷新本地记录的 `status`（如变为 `evaluated` / `failed`）
- [ ] 新增 `resumeHistory` store（参照 `frontend/src/stores/resumeStore.ts`），封装读/写/删/去重（按 `resume_id` 去重）逻辑并与 localStorage 同步
- [ ] 写入时若总数超过 10 条，自动丢弃最早的记录（上限 10 条）
- [ ] localStorage key 与数据结构在文档 Technical 部分明确
- [ ] Typecheck 通过

#### US-B2: 前端 - 我的简历页面

**Description:** As a user, I want a "My Resumes" page so that I can browse resumes I uploaded before.

**Acceptance Criteria:**
- [ ] 新增页面 `MyResumesPage`，路由 `/resumes`，注册于 `frontend/src/App.tsx` 的 `Layout` 路由组下
- [ ] 卡片式列表展示历史记录：文件名、上传时间、状态徽标
- [ ] 列表按上传时间倒序展示（最新在前）
- [ ] 进入页面时按各记录的 `resume_id` 拉取后端最新 `status` 刷新本地缓存（`GET /api/v1/resume/{id}/status`）；单条请求失败时回退展示本地缓存状态，不阻塞整页
- [ ] 本地列表最多保留 10 条，超出时自动丢弃最早的记录
- [ ] 空态：无历史记录时展示引导文案与"上传简历"按钮
- [ ] 视觉风格遵循 Neobrutalism
- [ ] Typecheck 通过
- [ ] 在浏览器中验证列表与空态

#### US-B3: 前端 - 查看/选择/删除本地记录

**Description:** As a user, I want to open, select, or remove entries in my resume list so that I can manage my history.

**Acceptance Criteria:**
- [ ] 点击某条记录跳转 `/resume/:id`（复用现有 `ResumePage` 详情页）
- [ ] 每条记录提供删除按钮，仅删除本地 localStorage 记录，不调用后端删除
- [ ] 删除有二次确认（避免误删）
- [ ] Typecheck 通过
- [ ] 在浏览器中验证查看与删除

#### US-B4: 前端 - 再次上传入口与导航

**Description:** As a user, I want quick access to upload a new resume so that I can keep adding resumes.

**Acceptance Criteria:**
- [ ] "我的简历"列表页与导航栏提供"上传新简历"入口，跳转 `/upload`
- [ ] 导航栏（`frontend/src/components/Layout.tsx`）新增"我的简历"入口，风格与现有 nav 按钮一致
- [ ] Typecheck 通过
- [ ] 在浏览器中验证导航跳转

#### US-B5: 前端 - i18n 文案

**Description:** As a bilingual user, I want the new UI in my language so that the experience is consistent.

**Acceptance Criteria:**
- [ ] 新增导航项、我的简历页、门禁弹窗、齿轮引导等全部文案补充中英文键
- [ ] 更新 `frontend/src/i18n/locales/zh.ts` 与 `en.ts`，key 命名与现有结构（`nav` / `upload` / `settings` 等）保持一致
- [ ] 品牌名（Provider 名称）不翻译，沿用现有约定
- [ ] Typecheck 通过

---

## Functional Requirements

- FR-1: 系统必须在 LLM 未"配置完成"（不存在 `is_active=true && verified=true` 的配置）时，硬拦截简历上传，禁止上传动作。
- FR-2: 系统必须在用户尝试上传且未就绪时，弹出提示 Modal，并提供跳转设置页的引导入口。
- FR-3: 后端必须为 `llm_configs` 增加 `verified` / `last_verified_at` 字段，并在连接测试通过时对已保存配置置为已验证；配置关键字段变更时重置为未验证。`verified` 不设时间过期。
- FR-4: 前端就绪判定必须以后端返回的 `is_active` + `verified` 为唯一数据源，供上传门禁与齿轮指示共享，二者状态必须一致。
- FR-5: 齿轮图标必须呈现三态状态徽标（未配置 / 已配置未验证 / 已验证），未就绪时醒目引导点击配置。
- FR-6: 系统必须在上传成功后将简历记录（resume_id、文件名、上传时间、状态）写入浏览器 localStorage，并在状态轮询时同步更新；本地列表最多保留 10 条，超出自动丢弃最早记录。
- FR-7: 系统必须提供"我的简历"页面（路由 `/resumes`），以卡片列表展示本地历史，含空态引导；进入页面时按 resume_id 拉取后端最新 status 刷新本地缓存。
- FR-8: "我的简历"页面必须支持查看（跳转详情页）、删除本地记录（含二次确认）、再次上传入口。
- FR-9: 系统必须在导航栏新增"我的简历"入口。
- FR-10: 所有新增文案必须覆盖中英文（i18n）。

---

## Non-Goals (Out of Scope)

- **不做**后端简历列表接口与数据库持久化的历史列表：本 PRD 明确"我的简历"为**浏览器 localStorage-only**，换设备或清除浏览器数据会丢失记录。
- **不做**多用户/权限体系（沿用现有匿名/硬编码 user 假设）。
- **不改**简历解析/评估管道的处理逻辑与状态机。
- **不做**简历跨设备同步、云端收藏、批量管理等高级能力。
- **不改**现有 LLM Provider/模型清单与加密存储机制。

---

## Design Considerations

### UI/UX
- 整体沿用 Neobrutalism 设计语言（粗边框、鲜明配色、硬阴影）。
- **门禁弹窗：** 使用醒目的警示配色卡片，主按钮"去配置"高对比度，文案直白说明为何被拦截。
- **齿轮状态徽标：** 在齿轮按钮右上角叠加小圆点/角标，红（脉冲）/黄/绿三态；未就绪时通过动画与文字强化引导。
- **我的简历列表：** 卡片式，每卡显示文件名、上传时间、状态徽标（复用现有 `Badge` 组件配色约定）；空态给出插画/文案 + "上传简历"按钮。
- **删除确认：** 复用现有确认交互模式（Modal 或行内确认），避免误删。

### 现有组件复用
- 复用 `Button` / `Card` / `Badge` / `Alert` / Modal 等 Neobrutalism 组件。
- 复用 `ResumePage`（`/resume/:id`）作为详情查看目标，避免新增详情页。
- 复用 `GET /api/v1/settings/llm` 判定就绪，不新增专用状态接口。

---

## Technical Considerations

### localStorage 数据结构
- key：`myResumes`（版本化可选，如内部带 `version` 字段便于未来迁移）
- value：JSON 数组，元素形如
  ```json
  {
    "resume_id": "uuid",
    "file_name": "resume.pdf",
    "uploaded_at": "2026-07-23T10:00:00.000Z",
    "status": "evaluated"
  }
  ```
- 去重：按 `resume_id` 去重；同一简历重复上传（后端返回相同 resume_id）时更新既有记录而非新增。
- 上限：最多保留 10 条，写入时超出则按 `uploaded_at` 丢弃最早记录。
- 状态刷新：进入"我的简历"页时逐条拉取 `GET /api/v1/resume/{id}/status` 刷新本地 `status`；请求失败回退本地缓存。

### 后端字段与迁移
- `llm_configs` 增加 `verified`(bool, default false)、`last_verified_at`(datetime, nullable)。
- 使用 Alembic 迁移，兼容既有数据（默认未验证）。
- `test_llm_connection` 支持可选 `config_id`：命中已保存配置时按测试结果更新 `verified`/`last_verified_at`；不传 `config_id` 时保持现有"仅测试不落库"行为。

### 前端
- 就绪判定集中于统一 store/hook，供 `UploadPage`、`Layout`（齿轮）、`SettingsPage` 共享。
- 应用启动/进入相关页面时拉取一次配置列表；设置页测试/保存后刷新就绪状态，保证齿轮与门禁实时一致。
- 技术栈沿用 React + Vite + TypeScript + Tailwind + Zustand + React Router + Neobrutalism。

---

## Success Metrics

- 未"配置完成"的用户 100% 被拦截并获得明确的配置引导，无法产生无效上传。
- 齿轮状态徽标与真实配置状态 100% 一致（配置变更/测试后即时更新）。
- "我的简历"历史记录在页面刷新、重开浏览器后保留（同一浏览器同源下）。
- 用户可从"我的简历"一键回看任意历史简历详情。

---

## Open Questions

> 以下问题已在需求确认中定稿：
>
> 1. ~~verified 是否需要过期策略~~ → **已确认**：不设过期，仅在配置关键字段变更或测试失败时失效。
> 2. ~~localStorage 历史列表条数上限~~ → **已确认**：最多保留 10 条，超出自动丢弃最早记录。
> 3. ~~列表是否展示后端最新状态~~ → **已确认**：进入页面时按 resume_id 拉取后端最新 status 刷新本地缓存，失败则回退本地。

暂无新的 Open Questions。
