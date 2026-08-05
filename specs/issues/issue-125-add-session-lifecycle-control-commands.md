# [AIP-015] Add Session lifecycle control commands

Add revision-safe pause, resume, skip, cancel, and terminate behavior under scenario and terminal-state rules.

## Acceptance Criteria

- [ ] Pause/resume preserve the same persisted current question and update active-time/expiry state.
- [ ] Pause during evaluating records `pause_requested`; finalization cannot expose a new active turn.
- [ ] Skip is allowed only before an accepted answer and within exact scenario allowance, with coverage/event updates.
- [ ] Cancel is start-only; terminate is post-start and preserves terminal `terminated` status.
- [ ] Every command requires expected revision, is idempotent where appropriate, and rejects expired/terminal/stale state.
- [ ] Transition/concurrency/integration tests cover every command and conflict pair.

- **Type:** backend
- **Priority:** high
- **Depends on:** #116, #124
- **SPEC:** AIP-015 sections 6.2, 7.3, 9
