# [AIP-014] Close Interview Plan privacy and concurrency acceptance

Verify plan generation/review/approval across all scenarios while proving private fields never cross transport/browser boundaries.

## Acceptance Criteria

- [ ] Exercise seven scenarios, four durations, three difficulties, two languages, coverage omissions, and low-score eligibility.
- [ ] Verify create/retry/approve/reject/regenerate, revision races, broker failure, timeout, and stale workers.
- [ ] Scan API responses, frontend state, logs, fixtures, and screenshots for private-plan/evaluation/privacy canaries.
- [ ] Verify approved snapshot immutability and one explicit Session-create action without automatic Session creation.
- [ ] Browser covers all entry points, refresh, mobile layout, conflict and recovery states.
- [ ] Required gates and complete Plan US/FR traceability are recorded.

- **Type:** fullstack / test
- **Priority:** high
- **Depends on:** #120
- **SPEC:** AIP-014 sections 10 through 12
