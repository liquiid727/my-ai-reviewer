# [RIP-010] Build Job Target workspace and version selectors

Add the minimal Job Target route and reusable immutable-version selectors for downstream flows.

## Acceptance Criteria

- [ ] Add `/targets/:id` with job/company/current JD Version/default Resume Version and recent activity summaries.
- [ ] Add typed target/version API modules and types without a second response/error decoder.
- [ ] Let users switch the default Resume Version with revision-conflict recovery.
- [ ] Render loading, empty, success, failure, mutation pending, conflict, and archived states in Chinese and English.
- [ ] Deep-link refresh resolves the requested target and never substitutes the latest target/version silently.
- [ ] Frontend test/lint/build and desktop/mobile browser checks pass.

- **Type:** frontend / fullstack
- **Priority:** high
- **Depends on:** #095
- **SPEC:** RIP-010 sections 8, 9, 11
