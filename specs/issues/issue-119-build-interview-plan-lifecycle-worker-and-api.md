# [AIP-014] Build Interview Plan lifecycle worker and API

Add async create/retry and revision-safe approve/reject/regenerate commands with public-only queries.

## Acceptance Criteria

- [ ] Validate one target/version/assessment/scenario tuple and allow every completed match score.
- [ ] Persist `generating`, dispatch after commit, and finalize only under current run/state ownership.
- [ ] Add create/list/detail/retry/approve/reject/regenerate endpoints and safe action flags.
- [ ] Enforce expected revision, approved immutability, linked regeneration, and broker/timeout failure behavior.
- [ ] Public DTOs contain no exact question, expected signal, rubric, private evidence, prompt, or provider output.
- [ ] Integration tests cover tuple mismatch, low score, retry, conflict, stale worker, and failed regeneration.

- **Type:** backend
- **Priority:** high
- **Depends on:** #118
- **SPEC:** AIP-014 sections 7, 9
