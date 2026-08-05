# [AIP-017] Build interview report and history UI

Add evidence-first report and high-density history views with explicit recommendation application/reconciliation.

## Acceptance Criteria

- [ ] Add `/interview-sessions/:id/report` and complete history filtering/recovery links.
- [ ] Show completion kind, dimensions, JD Coverage, evidence-backed strengths/risks, and insufficient-evidence labels with accessible text alternatives.
- [ ] Render waiting/failed/retry/complete/incomplete/zero-answer and legacy states accurately.
- [ ] Preview selected recommendations, confirm target RIP-008 plan, apply, and reconcile success/partial/conflict without losing selection.
- [ ] Keep report content immutable in UI and show applied task links as separate metadata.
- [ ] Chinese/English, component, build/lint, deep-link, desktop/mobile, accessibility, and no-overlap browser checks pass.

- **Type:** frontend / fullstack
- **Priority:** high
- **Depends on:** #138
- **SPEC:** AIP-017 sections 8, 9, 11
