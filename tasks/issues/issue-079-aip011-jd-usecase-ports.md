# [AIP-011] Extract JD application use cases and ports

Move JD import/extraction/storage/fetch/LLM orchestration behind application-owned contracts while preserving API behavior.

## Acceptance Criteria
- [x] JD domain imports no application or infrastructure implementation
- [x] Text/file/URL import, retry, re-extract, and match use cases have typed inputs/results
- [x] Fetch/parser/storage/LLM adapters are composed outside route/domain policy
- [x] URL safety, duplicate, failure, retry, API, and architecture tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #077
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 6-9)

## Status
- **State:** accepted (local-reviewed)
- **Review:** APPROVE_WITH_NITS (P3 only — concrete adapters in use cases; plan→application coupling deferred to #080; stage str outcomes; legacy settings gateway)
- **QA:** GREEN (jd unit 43, integration 12, arch unit 20, make arch-check new=0, ruff PASS)
- **Evidence:** tests/results/20260804T092700Z-aip011-issue-079-jd-usecase-ports.json
- **Delivery:** local-reviewed — no ship-it / no PR / no close
