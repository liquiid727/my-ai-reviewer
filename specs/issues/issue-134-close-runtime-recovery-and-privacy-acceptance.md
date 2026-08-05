# [AIP-016] Close runtime recovery and privacy acceptance

Verify the complete plan-driven text interview through coverage completion under retries, restarts, concurrency, and privacy constraints.

## Acceptance Criteria

- [ ] Exercise stage/coverage/follow-up/time/skip/candidate-question branches across representative scenarios.
- [ ] Verify duplicate answers/tabs, broker failure, timeout, watchdog, explicit retry, pause request, terminate, expiry, and stale workers.
- [ ] Restart API/worker/checkpointer and recover the same current question with no duplicate answer/evaluation/event.
- [ ] Scan DB, events, logs, responses, frontend state, fixtures, and screenshots for raw identifiers/private evaluation canaries.
- [ ] Browser validates full desktop/mobile flow and no live score/feedback exposure.
- [ ] Migration, unit, integration, worker, privacy, frontend, lint, type, build, diff, and traceability gates are recorded.

- **Type:** fullstack / test
- **Priority:** high
- **Depends on:** #128, #133
- **SPEC:** AIP-016 sections 10 through 12
