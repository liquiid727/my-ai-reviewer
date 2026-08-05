# [AIP-017] Apply report recommendations to RIP-008

Preview and apply selected recommendations through existing revision-checked manual-task commands with partial-result reconciliation.

## Acceptance Criteria

- [ ] Preview validates recommendation/plan/Job Target tuple and returns proposed task fields without mutation.
- [ ] Apply processes stable recommendation order and calls the RIP-008 application command, never its tables directly.
- [ ] Persist task mapping atomically with each successful plan revision mutation.
- [ ] Already-applied recommendations are idempotent successes and never duplicate tasks.
- [ ] Return all-success, zero-success conflict, and 207 partial applied/failed/not-attempted results with latest revision.
- [ ] Integration tests cover cancel, all success, repeated apply, mid-batch conflict, plan mismatch, and safe failure.

- **Type:** backend
- **Priority:** high
- **Depends on:** #112, #136
- **SPEC:** AIP-017 sections 6.3/6.4, 7.4, 9
