# [RIP-008] Task CRUD, revision control and plan progress

## Description

Implement conflict-safe task editing, ordering and automatic active/completed transitions.

## Acceptance Criteria
- [ ] Add manual task create, task patch, eligible task delete and full-order endpoints
- [ ] All mutations require expected_revision and atomically increment plan revision
- [ ] Revision mismatch returns 1007 without task writes
- [ ] Task fields and explicit nullable due date follow the SPEC validation contract
- [ ] Ordering requires every current task ID exactly once and rejects duplicates/missing IDs
- [ ] Enforce 200-task limit
- [ ] Progress is derived from persisted tasks and total=0 yields 0 percent
- [ ] Last completion sets completed; reopen/new task reactivates the plan
- [ ] Done task must be reopened before deletion
- [ ] Unit/integration tests cover repeated edits, conflicts, ordering and every state transition

## Dependencies

- `tasks/issues/issue-048-rip008-plan-task-schema.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-004; FR-11~FR-15

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 4.3, 5.4~5.5

