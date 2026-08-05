# [AIP-015] Add Session events and Coverage projection

Add atomic monotonic Session events and a mutable per-Session copy of approved plan coverage.

## Acceptance Criteria

- [ ] Create `interview_events` with unique Session sequence and allow-listed payload schemas per event type.
- [ ] Create `interview_session_coverage` with unique coverage key, status/evidence counts, and indexed references.
- [ ] Copy approved plan coverage on Session creation without mutating plan rows.
- [ ] Update Session state/coverage/event in one root-locked transaction with stable child lock order.
- [ ] Exclude text, score, feedback, prompt, completion, credentials, and replacement maps from all event payloads.
- [ ] Tests cover sequence races, rollback, projection rebuild, payload rejection, and query indexes.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** #122
- **SPEC:** AIP-015 sections 6.3/6.4, 7.1, 10.2/10.3
