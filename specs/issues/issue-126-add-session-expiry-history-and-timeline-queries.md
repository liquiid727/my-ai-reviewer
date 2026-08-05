# [AIP-015] Add Session expiry, history, and timeline queries

Add 30-day inactivity reconciliation and bounded list/detail/timeline projections for recovery and history.

## Acceptance Criteria

- [ ] Compute/extend `expires_at` from accepted user commands and reject post-expiry mutations.
- [ ] Add lazy single-resource reconciliation and Celery Beat batch watchdog without silent requeue/report generation.
- [ ] Add cursor list filters for target/scenario/status and detail action flags/current question/progress.
- [ ] Add cursor timeline over allow-listed events and no transcript/private-plan load.
- [ ] Batch/JOIN report/plan/target summaries without per-Session N+1.
- [ ] Tests cover deadline boundary, watchdog race, deep cursor ordering, expired recovery action, and query counts.

- **Type:** backend
- **Priority:** medium
- **Depends on:** #123, #125
- **SPEC:** AIP-015 sections 7.4, 8, 9, 10
