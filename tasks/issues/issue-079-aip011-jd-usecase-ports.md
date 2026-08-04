# [AIP-011] Extract JD application use cases and ports

Move JD import/extraction/storage/fetch/LLM orchestration behind application-owned contracts while preserving API behavior.

## Acceptance Criteria
- [ ] JD domain imports no application or infrastructure implementation
- [ ] Text/file/URL import, retry, re-extract, and match use cases have typed inputs/results
- [ ] Fetch/parser/storage/LLM adapters are composed outside route/domain policy
- [ ] URL safety, duplicate, failure, retry, API, and architecture tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #077
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 6-9)
