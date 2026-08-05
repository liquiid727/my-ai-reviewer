# [AIP-012] Migrate Resume errors and persisted failure state

Replace raw Resume exceptions/public `parse_error` leakage with stable safe errors and diagnostic correlation.

## Acceptance Criteria
- [ ] Resume upload/process/status/retry/reparse errors use the central taxonomy and mapper
- [ ] Raw exception text is absent from API responses and persisted user-visible failure state
- [ ] Privacy rejection, expiry, parser/LLM/storage failure, retryability, and stale run behavior are explicit
- [ ] Synthetic raw-error canaries are absent from API, DB-facing status, logs, and QA evidence

- **Type:** backend
- **Priority:** high
- **Depends on:** #078, #085
- **SPEC:** `specs/AIP-012-error-observability/spec.md` (Sections 6-11)
