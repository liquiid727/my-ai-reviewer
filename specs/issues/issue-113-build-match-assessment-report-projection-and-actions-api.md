# [RIP-014] Build Match Assessment report projection and actions API

Expose a completed Assessment as an evidence-backed report with exact versions, caps, gaps, staleness, and downstream action eligibility.

## Acceptance Criteria

- [ ] Build one bounded report projection over assessment, versions, target, and action eligibility without a second report store.
- [ ] Return pre/post-cap totals, eight dimensions, four gap classes, evidence sufficiency, policy/model metadata, and explicit unknowns.
- [ ] Mark newer current/default versions as an advisory stale condition without substituting inputs.
- [ ] Expose target assessment history with stable cursor ordering and no N+1.
- [ ] Keep low-score Interview Plan and RIP-008 actions enabled.
- [ ] API tests cover not-complete, stale, unknown evidence, legacy match separation, and safe public fields.

- **Type:** backend
- **Priority:** high
- **Depends on:** #110, #112
- **SPEC:** RIP-014 sections 6.1/6.3, 7.1/7.3, 9
