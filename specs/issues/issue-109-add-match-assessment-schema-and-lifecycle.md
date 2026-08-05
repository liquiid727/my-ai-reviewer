# [RIP-013] Add Match Assessment schema and lifecycle

Create the version-pinned Match Assessment aggregate with immutable completion, active-run uniqueness, and safe failure state.

## Acceptance Criteria

- [ ] Add `match_assessments` with target/version/policy/run/result/generator/failure fields and valid status/score/confidence checks.
- [ ] Index all foreign keys, completed-reuse lookup, target history, active watchdog, and partial active tuple uniqueness.
- [ ] Implement `queued/evaluating/completed/failed` transitions and completed immutability.
- [ ] Define normal reuse, force-new-row, failed retry, and stale-run rules.
- [ ] Reject target/version scope mismatches and deletion of referenced versions.
- [ ] Migration/domain/index tests pass from the current head.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** #092, #093, #107
- **SPEC:** RIP-013 sections 6.1, 7.2, 10
