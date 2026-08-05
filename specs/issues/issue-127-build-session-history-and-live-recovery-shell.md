# [AIP-015] Build Session history and live recovery shell

Add v2 Session list and live routes that recover server state and expose lifecycle controls before answer execution is connected.

## Acceptance Criteria

- [ ] Add `/interview-sessions` and `/interview-sessions/:id` with typed resource clients.
- [ ] List target, scenario, versions, status, progress, activity, and report summary with correct recovery action.
- [ ] Restore exact deep-linked current question/progress after refresh and never replace it with a newer Session.
- [ ] Implement start/pause/resume/skip/cancel/terminate controls with revision conflict/expiry reconciliation.
- [ ] Render loading, empty, failure, mutation pending, retryable, conflict, cancelled, terminated, expired, and legacy-link states.
- [ ] Chinese/English, component, build/lint, desktop/mobile, and stable-dimension layout checks pass.

- **Type:** frontend / fullstack
- **Priority:** high
- **Depends on:** #124, #126
- **SPEC:** AIP-015 sections 8, 9, 11
