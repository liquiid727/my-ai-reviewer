# [AIP-015] Close Session state and compatibility acceptance

Verify v2 Session state/events/recovery/expiry and prove v1 AIP-001 compatibility before adding turn execution.

## Acceptance Criteria

- [ ] Exercise create/start/pause/resume/skip/cancel/terminate/expiry and all revision/idempotency races.
- [ ] Verify event monotonicity/allow-list/rollback and relational projection recovery after checkpoint mismatch.
- [ ] Verify one non-cancelled Session per plan and stale worker cannot reopen terminal state.
- [ ] Run legacy v1 API/browser regression with representative existing rows/reports.
- [ ] Browser verifies deep links, multiple tabs, refresh, mobile controls, conflicts, expiry, and no private payload leakage.
- [ ] Migration, backend, frontend, privacy, query, lint, type, build, and traceability evidence are recorded.

- **Type:** fullstack / test
- **Priority:** high
- **Depends on:** #125, #127
- **SPEC:** AIP-015 sections 10 through 12
