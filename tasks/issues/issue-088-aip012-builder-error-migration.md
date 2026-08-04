# [AIP-012] Migrate Builder errors and frontend recovery mapping

Unify Builder API errors and map stable codes to translated editor recovery states.

## Acceptance Criteria
- [ ] Revision conflict, proposal invalidation, privacy replacement, imaging, render/export, and LLM errors use stable codes
- [ ] Multipart values, raw exceptions, and backend error objects are never echoed to users/logs
- [ ] Frontend distinguishes HTTP failure, business code, conflict/reload, retryable dependency failure, and expired state
- [ ] API/component/browser and synthetic-canary tests pass

- **Type:** fullstack
- **Priority:** high
- **Depends on:** #081, #084, #085
- **SPEC:** `specs/AIP-012-error-observability/spec.md` (Sections 7-11)
