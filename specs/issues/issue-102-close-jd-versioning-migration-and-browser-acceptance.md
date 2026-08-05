# [RIP-011] Close JD versioning migration and browser acceptance

Verify the complete existing-source import -> review -> publish -> version-history chain and record compatibility evidence.

## Acceptance Criteria

- [ ] Migration smoke covers legacy ready v1 backfill and new review constraints/indexes.
- [ ] Text/file/URL each reach review, publish, history, reparse failure recovery, and version-pinned downstream action.
- [ ] Duplicate, broker failure, timeout, stale run, referenced archive/delete, and concurrent edit/publish branches pass.
- [ ] Old JD API and RIP-003/RIP-008 compatibility tests remain green.
- [ ] Browser verifies desktop/mobile layouts, refresh persistence, conflicts, and no sensitive/error-object leakage.
- [ ] Required lint/type/test/build/diff gates and traceability evidence are recorded without claiming blocked checks passed.

- **Type:** fullstack / test
- **Priority:** high
- **Depends on:** #101
- **SPEC:** RIP-011 sections 10 through 12
