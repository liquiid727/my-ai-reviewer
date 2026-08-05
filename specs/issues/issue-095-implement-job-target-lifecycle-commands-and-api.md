# [RIP-010] Implement Job Target lifecycle commands and API

Provide idempotent downstream target creation, revision-safe defaults, archive, and bounded target queries.

## Acceptance Criteria

- [ ] `POST /job-targets` ensures an active target and handles uniqueness races by returning the winner.
- [ ] Validate default JD/Resume Version ownership and reject cross-identity tuples.
- [ ] Implement get/list, revision-checked default update, and archive commands through application use cases.
- [ ] Confirm importing, reviewing, publishing, and browsing a JD do not call target ensure.
- [ ] Return safe not-found/archived/revision/scope errors through the shared envelope.
- [ ] Integration tests cover first create, reuse, concurrent create, version switch, conflict, and archive.

- **Type:** backend
- **Priority:** high
- **Depends on:** #093, #094
- **SPEC:** RIP-010 sections 6.3, 7, 9.1/9.3
