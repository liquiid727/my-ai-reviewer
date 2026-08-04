# [RIP-008] Plan navigation, list and creation UI

## Description

Add the plan top-level route, persistent list and JD+resume creation workflow with deep-link preselection.

## Acceptance Criteria
- [ ] Add typed plan API client and `/plans`, `/plans/new`, `/plans/:id` routes
- [ ] Add Plan navigation beside JD navigation without header overlap
- [ ] List shows plan/JD/company/resume/progress/next due/status/updated time
- [ ] Search, status filter, empty/loading/generating/success/failure states work
- [ ] Create page loads ready JD and eligible resume options from backend
- [ ] `jd_id` or `resume_id` query preselects a valid option and rejects unavailable values visibly
- [ ] Add “创建计划” actions to ready JD detail and eligible resume list/detail surfaces, passing the corresponding query ID
- [ ] Generate remains disabled until both required selections are valid
- [ ] target date, weekly hours and supplemental background validations match API
- [ ] Duplicate plan response links to the existing plan
- [ ] Chinese/English copy, frontend lint/build and desktop/mobile browser verification pass

## Dependencies

- `tasks/issues/issue-046-rip007-jd-detail-ui.md`
- `tasks/issues/issue-051-rip008-plan-generation-api.md`

## Type

frontend / ui

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-002, US-006, US-007; FR-2~FR-6, FR-20, FR-22, FR-23

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 4.1~4.5, 9.3

