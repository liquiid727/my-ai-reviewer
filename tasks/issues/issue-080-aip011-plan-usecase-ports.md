# [AIP-011] Extract Plan application use cases and ports

Remove application/infrastructure imports from Plan domain services and keep generation/regeneration ownership in application use cases.

## Acceptance Criteria
- [ ] Plan domain contains pure policies/state rules only
- [ ] LLM config/generator and ORM access are behind typed ports/adapters
- [ ] Generation run ID, revision conflict, manual/completed task preservation, and retry semantics are unchanged
- [ ] Unit, API/task, stale-worker, and architecture tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #077
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 6-9)
