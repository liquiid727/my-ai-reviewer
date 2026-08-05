# [RIP-008] Plan create, list, detail and retry pipeline

## Description

Expose asynchronous initial generation with persistent states, duplicate-plan recovery, polling reads and safe retry.

## Acceptance Criteria
- [ ] Register plan Celery tasks with 180s limit and documented retry policy
- [ ] `POST /plans` validates LLM, ready JD, Candidate Profile and preferences before creating `generating`
- [ ] Duplicate unfinished pair returns code 1006 with existing plan ID
- [ ] Broker failure persists failed state and safe error
- [ ] Successful worker transaction inserts all AI tasks and sets active/generated_at/revision
- [ ] Initial failure inserts no partial tasks and supports `/retry` with a new run ID
- [ ] `GET /plans` supports pagination/search/status and computes progress/next due without N+1
- [ ] `GET /plans/{id}` returns tasks, revision, summaries and stale-generation flag
- [ ] Stale generation runs cannot write after retry/delete
- [ ] Integration tests cover create/success/failure/retry/duplicate/list/detail

## Dependencies

- `tasks/issues/issue-050-rip008-llm-plan-generator.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-002, US-003, US-005, US-006; FR-1, FR-4~FR-10, FR-20~FR-22

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 4.1~4.7, 5.1, 6.1

