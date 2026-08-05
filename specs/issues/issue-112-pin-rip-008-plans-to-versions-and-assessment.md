# [RIP-014] Pin RIP-008 plans to versions and assessment

Extend RIP-008 plan creation/generation to retain the exact Job Target, input versions, and Match Assessment without changing existing task behavior.

## Acceptance Criteria

- [ ] Add nullable indexed restrictive FKs for target/JD Version/Resume Version/Assessment.
- [ ] Add version-pinned unfinished-plan uniqueness while preserving legacy uniqueness semantics.
- [ ] Validate one coherent tuple and build plan Source Catalog from immutable snapshots.
- [ ] Keep legacy plan list/detail/edit/regenerate working with `input_contract=legacy` and null version refs.
- [ ] Regeneration of a version-pinned plan retains its original versions unless a new plan is explicitly created.
- [ ] RIP-008 run/revision/manual-task/progress and migration regression tests pass.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** issue #057, #111
- **SPEC:** RIP-014 sections 6.2, 7.2, 9, 10
