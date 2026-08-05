# [RIP-011] Build JD review and version-history UI

Upgrade `/jobs/:id` into a recoverable source-vs-structured review and immutable-version history workflow.

## Acceptance Criteria

- [ ] Compare read-only source content with structured fields/evidence/confidence in one page-level workflow.
- [ ] Support revision-safe edits, explicit publish, reparse, retry, abandon draft, and archive confirmations.
- [ ] Preserve local edits after save failure and reconcile revision conflicts without silent overwrite.
- [ ] Show draft/current/history states distinctly and open historical versions read-only.
- [ ] Enable downstream actions only with a current version and pass its exact ID.
- [ ] Cover loading/empty/processing/review/ready/failed/archived and desktop/mobile accessibility states.

- **Type:** frontend / fullstack
- **Priority:** high
- **Depends on:** #098, #099, #100
- **SPEC:** RIP-011 sections 8, 9, 11
