# [RIP-013] Implement match-v1 scoring and deterministic gap engine

Build the pure versioned scoring policy, Source Catalog normalization, caps, and non-conflicting gap classification.

## Acceptance Criteria

- [ ] Define the eight stable dimensions and exact 25/15/20/15/10/5/5/5 weights.
- [ ] Build typed JD/Resume Source Catalog IDs with normalized claims, provenance, confidence, and masked evidence.
- [ ] Implement weighted totals, two-decimal rounding, core-skill 75 cap, severe-years 70 cap, and lowest-cap rule.
- [ ] Treat unknown years/evidence as `evidence_gap` without applying unsupported caps.
- [ ] Produce one primary `capability_gap`, `expression_gap`, `evidence_gap`, or `hard_constraint_risk` per requirement.
- [ ] Policy/alias/threshold fixtures validate at startup and unit tests cover all boundary combinations.

- **Type:** backend
- **Priority:** high
- **Depends on:** #106
- **SPEC:** RIP-013 sections 6.2 through 6.5, 11
