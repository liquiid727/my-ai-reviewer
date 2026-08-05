# [AIP-012] Migrate JD and Plan errors

Adopt stable error/retry semantics across JD import/extraction and Plan generation/regeneration/task mutation.

## Acceptance Criteria
- [ ] Routes/services/tasks no longer expose provider, SQL, fetcher, parser, or raw `ValueError` text
- [ ] Validation, duplicate, not-ready, not-found, conflict, timeout, dependency, and stale-run errors map consistently
- [ ] Celery retry policy agrees with application `retryable` meaning
- [ ] JD/Plan API, task, conflict, retry, and canary tests pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #079, #080, #085
- **SPEC:** `specs/AIP-012-error-observability/spec.md` (Sections 6-11)
