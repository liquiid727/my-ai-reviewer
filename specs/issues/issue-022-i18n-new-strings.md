# i18n for New UI Strings

## Description

为本次新增的所有界面文案补充中英文 i18n，覆盖导航项、门禁弹窗、齿轮引导、我的简历页等。

PRD Reference: US-B5 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [ ] 更新 `frontend/src/i18n/locales/zh.ts` 与 `en.ts`，补充：导航"我的简历"、门禁弹窗文案、齿轮状态/引导提示、我的简历页（列表/空态/删除确认/上传新简历）等全部 key
- [ ] key 命名与现有结构（`nav` / `upload` / `settings` 等）保持一致
- [ ] 品牌名（Provider 名称）不翻译，沿用现有约定
- [ ] 中英文两套文案键完全对齐，无缺漏
- [ ] Typecheck 通过

## Dependencies

Issue #16, Issue #17, Issue #18, Issue #20, Issue #21

## Type

frontend

## Priority

P2
