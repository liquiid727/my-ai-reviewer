# [RIP-013] Build Match Assessment worker and API

Orchestrate idempotent create/reuse, async evaluation, retry, and public status/result queries.

## Acceptance Criteria

- [ ] `POST /match-assessments` validates exact versions and ensures/validates the active Job Target.
- [ ] Return a reused completed assessment or persist `queued` and dispatch after commit.
- [ ] Worker builds catalog, applies deterministic/semantic stages, and finalizes only under current run ownership.
- [ ] Broker failure, dependency timeout, invalid evidence, terminal failure, and explicit retry persist safe state.
- [ ] Add cursor list, detail, and retry endpoints with public immutable result schemas.
- [ ] Integration tests cover reuse, force, active duplicate, retry, stale worker, and low-score eligibility.

- **Type:** backend
- **Priority:** high
- **Depends on:** #108, #109
- **SPEC:** RIP-013 sections 7, 9
