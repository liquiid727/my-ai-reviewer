# [RIP-008] Plan integration, browser acceptance and traceability closeout

## Description

Verify the complete JD-to-plan chain and record delivery evidence without pulling Post-MVP TODO items into MVP scope.

## Acceptance Criteria
- [ ] Alembic, backend unit/integration, ruff, changed-module mypy, frontend lint and build pass
- [ ] End-to-end flow covers ready JD + eligible resume -> generation -> edit -> complete -> regenerate
- [ ] Browser verifies deep links from both JD and resume surfaces
- [ ] Browser verifies repeated autosave, revision conflict, retry and regeneration failure paths
- [ ] Desktop/mobile screenshots show both navigation entries and no text/control overlap
- [ ] RIP-007 referenced-delete regression passes after plan FK migration
- [ ] PRD US/FR to tests/issues traceability is complete in spec tasks/test evidence
- [ ] TODO-PLAN-001~008 remain documented as Post-MVP only and have no implementation code in this delivery
- [ ] `git diff --check` passes for delivery files

## Dependencies

- `tasks/issues/issue-047-rip007-jd-library-acceptance.md`
- `tasks/issues/issue-056-rip008-plan-regeneration-ui.md`

## Type

fullstack / test

## Priority

medium

## PRD Reference

`tasks/prd-job-search-plans.md` - All RIP-008 stories, success metrics and Post-MVP boundary

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 9 and 10.3
