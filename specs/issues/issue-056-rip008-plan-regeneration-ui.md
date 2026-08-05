# [RIP-008] Plan generation recovery and regeneration UI

## Description

Complete visible generation polling, failed retry and safe regeneration confirmation without losing displayed work.

## Acceptance Criteria
- [ ] generating/regenerating detail uses one 2s poller, backs off after 60s and stops in terminal/hidden/unmounted states
- [ ] Initial generation failure displays safe reason and retry without losing selected inputs
- [ ] Regeneration dialog explicitly says manual and done tasks are preserved and unfinished AI tasks are replaced
- [ ] During regeneration tasks remain readable and mutation controls are disabled
- [ ] Successful regeneration preserves manual/done rows and shows new AI rows after refresh
- [ ] Failed regeneration keeps the exact previous task list and displays retryable error
- [ ] Stale-generation banner offers explicit regenerate rather than automatic mutation
- [ ] Delete confirmation handles generating/regenerating state safely
- [ ] Frontend lint/build and desktop/mobile browser verification pass

## Dependencies

- `tasks/issues/issue-053-rip008-plan-regeneration.md`
- `tasks/issues/issue-055-rip008-plan-detail-editor-ui.md`

## Type

frontend / ui

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-003, US-005; FR-16~FR-19, FR-21

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 5.1, 5.6, 8.3, 9.3

