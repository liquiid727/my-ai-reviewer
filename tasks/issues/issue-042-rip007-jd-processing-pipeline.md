# [RIP-007] Celery JD processing and duplicate state machine

## Description

Build the idempotent source-to-LLM processing chain with stale-run protection, duplicate confirmation state and field provenance merging.

## Acceptance Criteria
- [ ] Register `backend.tasks.jd_tasks` in the Celery app
- [ ] Implement source extraction, duplicate check, LLM extraction and finalize steps with documented state transitions
- [ ] Every dispatch receives a new `processing_run_id`; stale runs exit without writes
- [ ] Normalize正文 with NFKC/whitespace rules and calculate SHA-256
- [ ] Matching content moves to `duplicate_pending` and records `duplicate_of_id`
- [ ] Worker obtains `get_active_verified_config` and constructs `LLMGateway.from_config`; no environment-model fallback
- [ ] LLM result expands title/company/location/seniority/responsibilities/required/preferred skills and validates limits
- [ ] Manual field sources are preserved unless `overwrite_manual=true`
- [ ] Failure stores safe error/step and does not leak provider responses or credentials
- [ ] Unit tests cover all transitions, retries, stale runs, duplicates, provenance and invalid LLM output

## Dependencies

- `tasks/issues/issue-040-rip007-jd-text-file-import.md`
- `tasks/issues/issue-041-rip007-secure-url-import.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-001, US-002, US-004, US-005; FR-8~FR-12, FR-14, FR-16, FR-17

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 5.1~5.5, 6.1

