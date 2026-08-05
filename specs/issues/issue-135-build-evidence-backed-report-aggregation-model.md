# [AIP-017] Build evidence-backed report aggregation model

Define deterministic complete/incomplete report aggregation and immutable report/recommendation persistence.

## Acceptance Criteria

- [ ] Aggregate seven report dimensions from persisted evaluations using scenario policy weights.
- [ ] Compute completion/answered/skipped/not-reached and JD Coverage summaries from relational projections.
- [ ] Require every strength/risk/recommendation evidence ID or explicit `insufficient_evidence`.
- [ ] Extend v2 report persistence with kind, coverage/evidence/policy/hash metadata and immutable content.
- [ ] Add separate recommendation rows with stable key/content and mutable apply metadata.
- [ ] Migration/domain tests cover complete, terminated incomplete, zero-answer ineligible, and legacy report labeling.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** #132, #134
- **SPEC:** AIP-017 sections 6.1 through 6.3, 10
