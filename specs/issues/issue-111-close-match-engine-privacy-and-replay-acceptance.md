# [RIP-013] Close match-engine privacy and replay acceptance

Verify scoring correctness, evidence integrity, replay behavior, worker convergence, and privacy as one backend acceptance gate.

## Acceptance Criteria

- [ ] Maintained synthetic fixtures cover all dimensions, caps, four gap classes, unknown evidence, and score bands.
- [ ] Same versions/policy/fake semantic output replay to the same score, caps, gaps, and explanations.
- [ ] Gateway spies and database/log/API checks contain no unmasked/direct-identifier canaries.
- [ ] Broker failure, timeout, malformed output, retry, concurrent force, and stale-worker cases converge safely.
- [ ] Representative list/reuse queries use expected indexes and bounded query counts.
- [ ] Migration, unit, integration, lint, type, privacy, and diff gates are recorded.

- **Type:** backend / test
- **Priority:** high
- **Depends on:** #110
- **SPEC:** RIP-013 sections 10 through 12
