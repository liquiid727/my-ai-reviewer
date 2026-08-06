# [RIP-011] Async matching service and compatibility APIs

## Description

Orchestrate hard filters, evidence-bound LLM dimensions and deterministic aggregation as an idempotent Celery run with versioned persistence and new v2 APIs, while leaving `rules_v1` behavior intact.

## Acceptance Criteria

- [ ] Implement create flow validation for ready JD, approved masked Candidate Profile/Facts and verified LLM
- [ ] Reuse an exact ready result or active run for the same fingerprint/mode; `force` bypasses only ready reuse
- [ ] Persist queued/running/ready/failed states and finalize only when run id and fingerprint still own the result
- [ ] Apply bounded transport retry, task timeout and one structured-output correction without partial ready writes
- [ ] Add create, detail, history/list and recompute endpoints under `/api/v1/jd/matches`
- [ ] Use application services from API routes and return the standard API envelope with safe errors
- [ ] Keep `POST /api/v1/jd/match` synchronous `rules_v1`, including inline JD and old response fields
- [ ] Query responses expose hard filters, dimensions, evidence, coverage/confidence, versions and stale reasons without raw resume content
- [ ] Integration tests cover idempotency, force, retry, timeout, dispatch failure, stale worker, history and all error branches
- [ ] Legacy API and persistence regression tests pass

## Dependencies

- `tasks/issues/issue-100-rip011-evidence-llm-matcher.md`

## Type

backend / workflow / API

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-007; FR-20~FR-24

## SPEC Reference

`specs/RIP-011-evidence-bound-jd-matching/spec.md` - Sections 7, 8, 9
