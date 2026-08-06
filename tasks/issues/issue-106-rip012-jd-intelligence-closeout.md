# [RIP-012] JD intelligence end-to-end and documentation closeout

## Description

Run the complete synthetic JD image -> Vision transcription -> structured JD -> evidence-bound match -> UI -> stale/recompute -> Plan/Interview consumption flow and close all documentation drift with reproducible evidence.

## Acceptance Criteria

- [ ] Create fixed synthetic image JD and masked Resume Facts/Profile fixtures with no real PII
- [ ] Verify image import, Vision transcription, duplicate handling, JD extraction/edit and ready state end to end
- [ ] Verify hard filters, seven dimensions, evidence links, deterministic recommendation and match result UI
- [ ] Modify JD and rebuild candidate facts/profile; verify old result becomes stale and a new immutable version is produced
- [ ] Verify Plan and Interview consume only fresh results and preserve their compatibility paths
- [ ] Verify stale/deleted late workers cannot overwrite any newer JD, match, plan or interview state
- [ ] Produce PRD FR -> SPEC -> issue -> code -> test -> evidence traceability with no missing links
- [ ] Reconcile RIP-003, RIP-007, RIP-008 and RIP-010~012 status/tasks against actual test evidence
- [ ] Run and record relevant migration, lint, type, unit, integration, frontend build/test and desktop/mobile browser gates
- [ ] Record environment blockers exactly; do not fabricate results or use real personal data in logs/screenshots
- [ ] Final `git diff --check` and scoped `git status --short` confirm no unrelated user changes were overwritten

## Dependencies

- `tasks/issues/issue-097-rip010-vision-import-acceptance.md`
- `tasks/issues/issue-102-rip011-matching-acceptance.md`
- `tasks/issues/issue-103-rip012-match-result-ui.md`
- `tasks/issues/issue-104-rip012-plan-match-freshness.md`
- `tasks/issues/issue-105-rip012-interview-match-context.md`

## Type

fullstack / qa / governance

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - All stories, FR-30 and Success Metrics

## SPEC Reference

`specs/RIP-012-jd-matching-consumption/spec.md` - Sections 7.4, 11~12
