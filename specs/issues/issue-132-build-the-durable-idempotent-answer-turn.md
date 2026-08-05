# [AIP-016] Build the durable idempotent answer turn

Add answer acceptance, async evaluation/next-turn worker, polling projection, retry, timeout, and stale-run convergence.

## Acceptance Criteria

- [ ] Require current question, expected revision, and `Idempotency-Key`; same key/payload reuses, mismatched payload conflicts.
- [ ] Mask direct identifiers, run PrivacyGuard, persist masked answer, set evaluating, write event, and commit before dispatch.
- [ ] Worker evaluates/generates outside transaction and finalizes evaluation/coverage/next question/events only under current ownership.
- [ ] Enforce 180-second deadline, bounded transient retry, broker failure, watchdog retryable state, and explicit user retry.
- [ ] Respect pause request/terminate/expiry and prevent stale worker terminal-state rewrites.
- [ ] API responses/live projections contain no evaluation score, feedback, signal, rubric, or private-plan fields.

- **Type:** backend
- **Priority:** high
- **Depends on:** #125, #131
- **SPEC:** AIP-016 sections 6.3/6.4, 7.2 through 7.4, 9
