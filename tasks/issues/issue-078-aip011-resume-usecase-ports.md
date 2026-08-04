# [AIP-011] Extract Resume application use cases and ports

Move Resume parsing/privacy/storage/LLM orchestration out of domain and route code behind typed use cases and ports.

## Acceptance Criteria
- [ ] Resume domain imports no application, ORM, storage, parser, privacy adapter, or LLM implementation
- [ ] Upload/process/retry/reparse ownership is explicit in application use cases
- [ ] Infrastructure adapters are wired at composition and stale run/privacy behavior is preserved
- [ ] Characterization, API, privacy, task, and architecture tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #077
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 6-9)
