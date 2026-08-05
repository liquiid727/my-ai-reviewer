# [AIP-017] Build report, history, and timeline projections

Expose immutable report detail, report retry, recommendation state, and bounded Session/history/timeline queries.

## Acceptance Criteria

- [ ] Add Session report status/detail and report-by-ID endpoints with complete/incomplete/insufficient semantics.
- [ ] Add report retry command and recommendation preview/apply endpoints with safe public schemas.
- [ ] Add cursor Session history filters and timeline projection with report summary/recovery actions.
- [ ] JOIN/batch target/plan/report/recommendation summaries without transcript/private-plan/full-report N+1 loads.
- [ ] Keep v1 legacy reports on legacy routes and clearly label their contract.
- [ ] API/query tests cover waiting/failure/retry/complete/incomplete/partial apply/cursor and private-field absence.

- **Type:** backend
- **Priority:** high
- **Depends on:** #123, #136, #137
- **SPEC:** AIP-017 sections 7.2, 8, 9
