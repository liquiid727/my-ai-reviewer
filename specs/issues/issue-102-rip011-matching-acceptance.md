# [RIP-011] Matching privacy, model-regression and acceptance closeout

## Description

Close RIP-011 with migration, hard-filter, evidence, privacy, concurrency, model-regression and compatibility evidence using deterministic synthetic inputs and mocked LLM outputs.

## Acceptance Criteria

- [ ] Run migration/backfill tests and verify old `rules_v1` records remain readable
- [ ] Execute hard-filter pass/fail/unknown and all aggregation threshold/coverage cases
- [ ] Verify every ready LLM dimension references valid Catalog evidence and unsupported claims are rejected
- [ ] Run synthetic prompt/schema/model drift fixtures and record behavior changes by matcher version
- [ ] Verify JD edit/reextract, resume reparse, facts/profile rebuild and matcher/prompt/schema/model changes produce expected stale reasons
- [ ] Assert provider spies, logs, errors and snapshots contain no raw resume, identity, direct identifiers, prompt or keys
- [ ] Exercise duplicate requests, retry, timeout and late-worker concurrency
- [ ] Run legacy `POST /jd/match`, plan-source and JD import regressions
- [ ] Update design/database/API and RIP-011 tasks from actual implementation evidence
- [ ] Record exact lint/type/unit/integration statuses and `git diff --check`; do not convert NOT_RUN/BLOCKED to PASS

## Dependencies

- `tasks/issues/issue-101-rip011-async-matching-api.md`

## Type

backend / qa / privacy

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-005~US-007, US-010; Success Metrics

## SPEC Reference

`specs/RIP-011-evidence-bound-jd-matching/spec.md` - Sections 11~12
