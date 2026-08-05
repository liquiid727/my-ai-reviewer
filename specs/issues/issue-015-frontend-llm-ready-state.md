# Frontend LLM Ready-State (Shared Source of Truth)

## Description

前端建立"LLM 是否就绪"的唯一数据源，供上传门禁与齿轮状态指示共享，避免逻辑重复与状态不一致。就绪 = 存在 `is_active=true && verified=true` 的配置。

PRD Reference: US-A2 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [ ] `frontend/src/types/settings.ts` 的 `LLMConfig` 增加 `verified: boolean` 与 `last_verified_at: string | null`
- [ ] 复用 `GET /api/v1/settings/llm`（`frontend/src/api/settings.ts`）拉取配置列表
- [ ] 就绪判定集中管理（新增 `settingsStore` 或统一 hook），暴露 `isLLMReady` 状态
- [ ] 提供刷新方法，供设置页测试/保存后主动刷新就绪状态
- [ ] Typecheck (tsc) 通过

## Dependencies

Issue #14

## Type

frontend

## Priority

P1
