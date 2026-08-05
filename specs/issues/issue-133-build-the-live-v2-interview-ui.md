# [AIP-016] Build the live v2 interview UI

Connect the Session page to durable answer turns while preserving interview rhythm and withholding feedback.

## Acceptance Criteria

- [ ] Add stable current-question, masked answer editor, stage/progress, pending state, and lifecycle control regions.
- [ ] Submit once with idempotency/revision, disable duplicates, and poll until ready/retryable/terminal.
- [ ] Handle follow-up, skip, pause/resume, terminate, retryable failure, conflict, expiry, refresh, and ownership cleanup.
- [ ] Do not place score/feedback/rubric/private-plan data in API types, store, DOM, toast, or browser history.
- [ ] Keep input/control dimensions stable across long text, pending/error, desktop/mobile, and localization.
- [ ] Component, build/lint, deep-link, keyboard/accessibility, and real browser checks pass.

- **Type:** frontend / fullstack
- **Priority:** high
- **Depends on:** #127, #132
- **SPEC:** AIP-016 sections 8, 9, 11
