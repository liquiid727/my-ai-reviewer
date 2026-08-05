# [AIP-014] Build Interview Plan create and review UI

Add one creation flow and public strategy review route without exposing private plan data.

## Acceptance Criteria

- [ ] Add target input/version/assessment and scenario/duration/difficulty/language selectors.
- [ ] Enter from JD, Resume, Match report, and Job Target with valid preselection and explicit switching.
- [ ] Poll generation safely and render loading/empty/failure/timeout/retry/conflict/stale states.
- [ ] Show stages, objectives, coverage, risk focus, budgets, and duration; never store/render private question/rubric fields.
- [ ] Support revision-safe approve, reject, and regenerate with clear confirmations/recovery.
- [ ] Chinese/English, component, build/lint, deep-link, desktop/mobile, and accessibility checks pass.

- **Type:** frontend / fullstack
- **Priority:** high
- **Depends on:** #114, #116, #119
- **SPEC:** AIP-014 sections 8, 9, 11
