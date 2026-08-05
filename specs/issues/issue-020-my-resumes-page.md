# My Resumes Page

## Description

新增"我的简历"页面，卡片式展示本地历史列表，支持查看跳转详情、删除本地记录（二次确认），进入页面时按 resume_id 拉取后端最新状态刷新本地缓存，含空态引导。

PRD Reference: US-B2, US-B3 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [ ] 新增页面 `MyResumesPage`，路由 `/resumes`，注册于 `frontend/src/App.tsx` 的 `Layout` 路由组下
- [ ] 卡片式列表展示：文件名、上传时间、状态徽标，按上传时间倒序（最新在前）
- [ ] 进入页面时按各记录 `resume_id` 拉取 `GET /api/v1/resume/{id}/status` 刷新本地缓存；单条失败回退本地状态，不阻塞整页
- [ ] 本地列表最多保留 10 条
- [ ] 点击某条记录跳转 `/resume/:id`（复用现有 `ResumePage`）
- [ ] 每条提供删除按钮，仅删除本地 localStorage 记录（不调用后端删除），含二次确认
- [ ] 空态：无历史记录时展示引导文案与"上传简历"按钮
- [ ] 视觉风格遵循 Neobrutalism
- [ ] Typecheck 通过
- [ ] 在浏览器中验证列表、空态、查看、删除

## Dependencies

Issue #19

## Type

frontend

## Priority

P1
