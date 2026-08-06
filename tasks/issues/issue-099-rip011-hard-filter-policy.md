# [RIP-011] Deterministic hard-filter policy

## Description

Implement pure domain evaluation for explicit, enforceable JD hard requirements and deterministic score/recommendation aggregation. Keep unknown evidence distinct from failure and require human confirmation.

## Acceptance Criteria

- [ ] Support required skill, minimum experience, required certificate, location and work-authorization requirement types
- [ ] Evaluate each requirement as pass/fail/unknown with JD and candidate evidence IDs
- [ ] Only explicit enforceable requirements can produce fail; missing or ambiguous facts produce unknown
- [ ] Implement seven dimension weights and nullable dimension scores exactly as specified
- [ ] Normalize provisional scores over known dimensions and return `manual_review` below 60% coverage or with enforceable unknowns
- [ ] Return `hard_filter_review` for hard fail and set `human_confirmation_required=true`
- [ ] Compute all recommendations deterministically and ignore any LLM recommendation field
- [ ] Preserve existing `compute_match` behavior as the unchanged `rules_v1` policy
- [ ] Pure unit tests cover every operator/status, aliases, thresholds, boundary values, missing/conflicting facts and empty inputs

## Dependencies

- `tasks/issues/issue-098-rip011-matching-contracts.md`

## Type

backend / domain

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-005, US-006; FR-11~FR-13, FR-16, FR-18, FR-19

## SPEC Reference

`specs/RIP-011-evidence-bound-jd-matching/spec.md` - Sections 6.2, 6.4
