# [RIP-014] Build unified match creation and report UI

Make JD, resume, matching-center, and Job Target entry points converge on one version-pinned creation/report workflow.

## Acceptance Criteria

- [ ] Add typed Match Assessment API/types and target match routes.
- [ ] Preselect source-context versions but allow explicit ready-version switching before submit.
- [ ] Represent loading, empty, queued, evaluating, completed, failed, timeout, retry, stale, and mutation-pending states.
- [ ] Render score dimensions, caps, gaps, evidence sufficiency, and advisory wording without overstating unknown evidence.
- [ ] Provide explicit resume optimization, RIP-008 plan, and Interview Plan actions; low score never disables interview action.
- [ ] Chinese/English, component, build/lint, deep-link, and desktop/mobile browser checks pass.

- **Type:** frontend / fullstack
- **Priority:** high
- **Depends on:** #096, #113
- **SPEC:** RIP-014 sections 8, 9, 11
