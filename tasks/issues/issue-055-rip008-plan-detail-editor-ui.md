# [RIP-008] Plan detail task editor and autosave

## Description

Deliver repeated, conflict-safe plan execution interactions for task editing, completion and ordering.

## Acceptance Criteria
- [ ] Detail renders plan summaries, stale indicator, progress and category-organized tasks
- [ ] Status checkbox/select saves immediately; text/date/priority edits debounce 500ms
- [ ] Mutations for one task are serialized and use latest returned revision
- [ ] User can create manual tasks, edit allowed fields, reopen and delete eligible tasks
- [ ] Ordering persists and remains stable after refresh
- [ ] Save failure retains local draft and offers retry
- [ ] Revision conflict stops queued writes, refreshes server state and prompts reconciliation
- [ ] Completion/reopen updates progress and plan state without page reload
- [ ] Loading text, task labels and controls do not resize/overlap the layout
- [ ] Frontend lint/build and browser verification cover second and later interactions

## Dependencies

- `tasks/issues/issue-052-rip008-plan-task-crud.md`
- `tasks/issues/issue-054-rip008-plan-list-create-ui.md`

## Type

frontend / ui

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-004; FR-11~FR-15

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 4.3~4.4, 8.3, 9.3

