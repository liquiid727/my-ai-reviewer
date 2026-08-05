# [RIP-011] Publish immutable JD versions and history API

Add explicit idempotent publication and read-only version history from the reviewed draft.

## Acceptance Criteria

- [ ] `POST /jd/{id}/publish` validates the expected review revision and complete canonical snapshot.
- [ ] Insert the immutable version and switch `current_version_id` in one short transaction.
- [ ] Resolve repeated same-content/schema publication to the existing version.
- [ ] Expose cursor history and exact version detail with source/generator/publication metadata.
- [ ] Published rows have no PATCH/delete command and downstream links use `jd_version_id`.
- [ ] Tests prove old version content remains unchanged after later publications.

- **Type:** backend
- **Priority:** high
- **Depends on:** #092, #098
- **SPEC:** RIP-011 sections 6.2, 7.1, 9, 10
