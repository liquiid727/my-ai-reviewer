# [RIP-010] Add Job Target schema and active-target invariants

Add the minimal Job Target aggregate and enforce one active target per JD identity in the current anonymous scope.

## Acceptance Criteria

- [ ] Add `job_targets` with JD/default-version references, revision, timestamps, and archive state.
- [ ] Add the partial unique active-JD index and all foreign-key/list indexes.
- [ ] Implement pure rules for default-version ownership, revision increment, archive, and historical preservation.
- [ ] Prove concurrent inserts cannot leave duplicate active targets.
- [ ] Document that future user/tenant ownership requires a separate migration rather than silently widening this invariant.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** #092
- **SPEC:** RIP-010 sections 6.3, 10.3, 11
