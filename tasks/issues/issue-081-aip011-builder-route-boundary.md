# [AIP-011] Extract Builder route side effects

Make Builder routes transport-only by moving imaging, storage, LLM, rendering, and transaction orchestration into application use cases.

## Acceptance Criteria
- [ ] Builder router imports no MinIO, imaging, LLM gateway, renderer, or ORM model implementation
- [ ] Preview/export multipart/binary contracts remain feature-scoped and compatible
- [ ] Revision, photo, privacy replacement, proposal, and error ownership is explicit
- [ ] API, export/privacy, conflict, and architecture tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #077
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 5, 7-9)
