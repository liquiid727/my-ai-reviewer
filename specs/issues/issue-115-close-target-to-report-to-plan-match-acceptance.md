# [RIP-014] Close target-to-report-to-plan match acceptance

Verify the complete Job Target -> Assessment -> report -> RIP-008/Interview Plan entry chain and trace all Match PRD requirements.

## Acceptance Criteria

- [ ] Exercise first target creation, version selection, async assessment, evidence report, and plan handoff end to end.
- [ ] Verify completed reuse, force re-evaluate, stale advisory, conflict, timeout, retry, and low-score training.
- [ ] Verify version-pinned RIP-008 plan generation/regeneration remains reproducible and legacy plans remain compatible.
- [ ] Browser validates all four entry points, refresh persistence, mobile layout, safe errors, and no version substitution.
- [ ] Query-count/index and privacy canary checks pass.
- [ ] Required gates and complete Match US/FR-to-test traceability are recorded.

- **Type:** fullstack / test
- **Priority:** high
- **Depends on:** #111, #114
- **SPEC:** RIP-014 sections 10 through 12
