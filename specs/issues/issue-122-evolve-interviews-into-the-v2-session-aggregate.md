# [AIP-015] Evolve interviews into the v2 Session aggregate

Extend the existing `interviews` persistence root for plan-driven v2 Sessions while preserving all legacy AIP-001 rows/routes.

## Acceptance Criteria

- [ ] Add `contract_version`, approved-plan reference, revision, Session/turn/report states, activity/expiry, current question, ownership, and safe failure fields.
- [ ] Add valid state/check constraints, all foreign-key/cursor/watchdog indexes, and partial one-non-cancelled-Session-per-plan uniqueness.
- [ ] Define pure v2 Session transition/guard rules and exact legacy/v2 serializer dispatch.
- [ ] Backfill existing rows as contract version 1 without synthesizing plan/events/coverage.
- [ ] Prove legacy `/interview` create/start/answer/status/report/list behavior remains unchanged.
- [ ] Migration upgrade/downgrade and representative v1/v2 model tests pass.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** #121
- **SPEC:** AIP-015 sections 6.1/6.2, 8, 10.1/10.4
