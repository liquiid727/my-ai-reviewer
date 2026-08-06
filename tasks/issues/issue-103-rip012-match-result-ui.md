# [RIP-012] JD multidimensional match result UI

## Description

Replace the match-success-only interaction on JD Detail with a typed, explainable `hybrid_v2` result panel and safe recompute workflow.

## Acceptance Criteria

- [ ] Extend frontend JD API/types to represent nullable score, hard filters, seven dimensions, evidence, coverage/confidence, versions and stale reasons
- [ ] Show eligible resume selection and empty/loading/queued/running/ready/failed/stale/recompute-pending/timed-out states
- [ ] Display hard filter pass/fail/unknown separately from soft scores, including human-confirmation notice
- [ ] Display dimension score/status/reason and linked JD/candidate evidence without exposing raw resume text
- [ ] Show risk, gap, recommendation, evidence coverage and model-analysis disclaimer
- [ ] Stale results show stable reasons and a recompute action; active runs disable duplicate submissions
- [ ] Polling stops on terminal state, timeout, page hide, unmount or selection change
- [ ] Chinese/English i18n, accessibility names and responsive layout are complete
- [ ] Component tests cover every state and browser verification covers desktop/mobile success, failure, stale and recompute

## Dependencies

- `tasks/issues/issue-102-rip011-matching-acceptance.md`

## Type

frontend / ui

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-008; FR-25

## SPEC Reference

`specs/RIP-012-jd-matching-consumption/spec.md` - Sections 6.2, 7.1, 9.1, 11
