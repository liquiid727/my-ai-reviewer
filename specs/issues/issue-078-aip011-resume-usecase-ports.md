# [AIP-011] Extract Resume application use cases and ports

Move Resume parsing/privacy/storage/LLM orchestration out of domain and route code behind typed use cases and ports.

## Acceptance Criteria
- [x] Resume domain imports no application, ORM, storage, parser, privacy adapter, or LLM implementation
- [x] Upload/process/retry/reparse ownership is explicit in application use cases
- [x] Infrastructure adapters are wired at composition and stale run/privacy behavior is preserved
- [x] Characterization, API, privacy, task, and architecture tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #077
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 6-9)

## Status
- **Status:** accepted (local-reviewed)
- **Review:** APPROVE_WITH_NITS R1
- **QA:** GREEN R1
- **Evidence:** `tests/results/20260804T090926Z-aip011-issue-078-resume-usecase-ports.json`
