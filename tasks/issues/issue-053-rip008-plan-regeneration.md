# [RIP-008] Atomic plan regeneration and protected deletion

## Description

Regenerate only replaceable AI work while preserving manual/completed tasks and keeping the original set on failure.

## Acceptance Criteria
- [ ] `/regenerate` validates revision, current state, upstream inputs and duplicate unfinished plan conflicts
- [ ] Regeneration creates a new run ID and blocks concurrent task mutations with code 1003
- [ ] LLM generation completes outside the replacement transaction
- [ ] Final transaction locks the plan and verifies current run ID
- [ ] Preserve every manual task and every done task
- [ ] Replace only unfinished AI tasks and append new AI tasks in stable order
- [ ] Success updates match/snapshot/model/generated_at/status/revision atomically
- [ ] Failure restores previous plan status and leaves all tasks unchanged
- [ ] Delete invalidates the run and cascades tasks without deleting JD/resume/match
- [ ] Regeneration preservation matrix and failure atomicity tests pass

## Dependencies

- `tasks/issues/issue-050-rip008-llm-plan-generator.md`
- `tasks/issues/issue-052-rip008-plan-task-crud.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-005; FR-16~FR-19

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 5.6~5.7, 6.2~6.3

