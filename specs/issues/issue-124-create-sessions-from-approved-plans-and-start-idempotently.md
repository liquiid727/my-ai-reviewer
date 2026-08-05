# [AIP-015] Create Sessions from approved plans and start idempotently

Implement idempotent v2 Session creation and start from an immutable approved Interview Plan.

## Acceptance Criteria

- [ ] `POST /interview-sessions` accepts only plan ID and copies exact approved snapshot references.
- [ ] Repeated/concurrent create returns the existing non-cancelled Session; rejected/failed/unapproved plans are refused.
- [ ] Idempotent start persists/returns one first public question and writes ordered start/question events.
- [ ] Start never returns the remaining private plan or hidden signals/rubrics.
- [ ] Set revision/activity/expiry/current-question fields in short atomic transactions.
- [ ] Integration tests cover duplicate create/start, cancelled replacement, invalid plan, and private-field absence.

- **Type:** backend
- **Priority:** high
- **Depends on:** #119, #122, #123
- **SPEC:** AIP-015 sections 6.1/6.2, 7.2, 9
