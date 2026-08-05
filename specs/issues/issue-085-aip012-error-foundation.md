# [AIP-012] Add error taxonomy and API mapper foundation

Introduce transport-independent errors plus one global HTTP/envelope mapping contract.

## Acceptance Criteria
- [ ] Errors carry stable code, safe message, retryable flag, allow-listed details, and chained cause
- [ ] Domain/application errors contain no FastAPI or HTTP status dependency
- [ ] Validation, not-found, state, conflict, expired, dependency, timeout, privacy, and unknown mappings are explicit
- [ ] Unknown errors return a generic message and request ID while internal logs retain a redacted stack

- **Type:** backend
- **Priority:** high
- **Depends on:** #074
- **SPEC:** `specs/AIP-012-error-observability/spec.md` (Sections 5-9)
