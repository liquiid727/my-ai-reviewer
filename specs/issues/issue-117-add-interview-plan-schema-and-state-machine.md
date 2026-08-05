# [AIP-014] Add Interview Plan schema and state machine

Create the version-pinned Interview Plan aggregate with separate public/private snapshots and immutable approval semantics.

## Acceptance Criteria

- [ ] Add `interview_plans` with target/version/assessment/scenario/config, run/revision/state, public/private, hash, and safe failure fields.
- [ ] Index all FKs, target history, review/active run, and supersession paths.
- [ ] Implement valid generating/review/approved/rejected/failed/superseded transitions.
- [ ] Approved is immutable; regeneration creates a linked replacement row.
- [ ] Define public strategy/Coverage Matrix and private question/signal/rubric schemas separately.
- [ ] Migration/domain/serialization tests pass and no private serializer can be constructed accidentally.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** #111, #116
- **SPEC:** AIP-014 sections 6.1 through 6.4, 10
