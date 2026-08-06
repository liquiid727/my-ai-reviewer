# [RIP-012] Job Search Plan match freshness integration

## Description

Upgrade RIP-008 match selection and plan snapshots to consume only fingerprint-fresh `hybrid_v2` results without changing the existing plan lifecycle, revision or regeneration guarantees.

## Acceptance Criteria

- [ ] Replace timestamp-only match freshness with the shared fingerprint policy and stable stale reasons
- [ ] Reuse exact fresh `hybrid_v2`; recompute missing/stale results through the v2 application service
- [ ] Fail safely when recompute fails or times out; never silently use stale results as fresh
- [ ] Save match id/mode/fingerprint and matcher/policy/prompt/schema/provider/model into the plan input snapshot
- [ ] Include bounded dimension/gap evidence in the plan Source Catalog without identity or raw resume data
- [ ] Existing plan create/retry/regenerate/task revision contracts remain compatible
- [ ] Input changes mark generated plans stale but do not mutate historical/manual/done tasks until explicit regenerate
- [ ] Tests cover each freshness input, fresh reuse, recompute success/failure, late workers and atomic regenerate preservation
- [ ] Update RIP-008 match-selection and snapshot sections to the as-built v2 contract

## Dependencies

- `tasks/issues/issue-101-rip011-async-matching-api.md`
- RIP-008 existing implementation baseline

## Type

backend / integration

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-009; FR-23, FR-24, FR-26

## SPEC Reference

`specs/RIP-012-jd-matching-consumption/spec.md` - Sections 6.1, 7.2, 9.2
