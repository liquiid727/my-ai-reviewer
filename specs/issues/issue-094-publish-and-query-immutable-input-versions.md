# [RIP-010] Publish and query immutable input versions

Implement application-owned publication/query interfaces for exact masked Resume Versions and read-only JD Versions.

## Acceptance Criteria

- [ ] Publish or resolve an evaluated parsed resume or exact saved Builder revision without accepting arbitrary client snapshots.
- [ ] Canonicalize/hash input, run PrivacyGuard, and persist masked/profile/evidence snapshots only.
- [ ] Expose typed Resume Version create/list/detail and JD Version list/detail endpoints under `/api/v1`.
- [ ] Make same-source/same-content publication idempotent and detect source-revision races.
- [ ] Cursor queries return summaries without loading full snapshots; detail never returns real-value mappings.
- [ ] Unit/integration/privacy tests cover both source types, not-ready, conflict, not-found, and canary leakage.

- **Type:** backend
- **Priority:** high
- **Depends on:** #092
- **SPEC:** RIP-010 sections 6.1/6.2, 7.1/7.2, 9
