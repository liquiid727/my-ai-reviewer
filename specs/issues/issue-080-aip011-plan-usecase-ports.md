# [AIP-011] Extract Plan application use cases and ports

Remove application/infrastructure imports from Plan domain services and keep generation/regeneration ownership in application use cases.

## Acceptance Criteria
- [x] Plan domain contains pure policies/state rules only
- [x] LLM config/generator and ORM access are behind typed ports/adapters
- [x] Generation run ID, revision conflict, manual/completed task preservation, and retry semantics are unchanged
- [x] Unit, API/task, stale-worker, and architecture tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #077
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 6-9)


## Status
- **Status:** accepted (local-reviewed)
- **Decision:** GREEN
- **Evidence:** `tests/results/20260804T110000Z-aip011-issue-080-plan-usecase-ports.json`
- **Review:** pending dual Reviewer+QA
