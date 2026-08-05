# [RIP-007] JD navigation, list and three-mode import UI

## Description

Add the JD top-level route and the primary list/import workflow using the backend as the data source.

## Acceptance Criteria
- [ ] Add typed JD API client and `/jobs` route
- [ ] Add JD navigation in the screenshot-designated header area without layout overlap
- [ ] List renders title/company/source/seniority/status/update time with paging, search and filters
- [ ] Empty, loading, success and load-failure states are distinct and stable
- [ ] Import dialog uses segmented text/file/URL modes and disables invalid submissions
- [ ] LLM-not-ready opens the existing configuration gate
- [ ] Processing records appear immediately and a single list-level poller updates terminal states
- [ ] Duplicate pending state offers confirm/cancel actions
- [ ] Chinese/English copy, frontend lint and typecheck pass
- [ ] Verify desktop and mobile behavior in a browser

## Dependencies

- `tasks/issues/issue-044-rip007-jd-state-command-api.md`

## Type

frontend / ui

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-003, US-004; FR-1~FR-6, FR-15~FR-17

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 2.4, 8.3, 9.3

