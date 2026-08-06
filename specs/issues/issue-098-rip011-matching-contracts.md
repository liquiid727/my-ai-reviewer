# [RIP-011] Versioned matching domain and data contracts

## Description

Define and migrate the stable input/result contracts for `hybrid_v2`, including JD hard requirements, immutable minimized snapshots, lifecycle status, versions and fingerprints while preserving legacy match rows.

## Acceptance Criteria

- [ ] Add typed JD hard-requirement, dimension, evidence, lifecycle and v2 result schemas
- [ ] Add `structured_revision` and bounded `hard_requirements` to JD without breaking existing extraction fields
- [ ] Extend `jd_match_results` with status/mode/run/fingerprint/snapshot/dimensions/evidence/coverage/confidence/version/model/failure timestamps
- [ ] Backfill existing rows as `rules_v1`, `ready`, `matcher_version=rules-v1` while preserving old fields
- [ ] Add constraints/indexes for lifecycle and exact-input idempotency without deleting historical results
- [ ] Define fingerprint inputs for JD, masked facts/profile and matcher/policy/prompt/schema/model versions
- [ ] Define stable stale-reason codes and compatibility serialization for old clients
- [ ] Migration upgrade, legacy backfill, constraints and downgrade behavior are tested
- [ ] Domain schemas have no ORM, LLM, Celery or provider dependencies

## Dependencies

- `tasks/issues/issue-092-jd-intelligence-drift-baseline.md`
- `tasks/issues/issue-097-rip010-vision-import-acceptance.md`

## Type

backend / domain / database

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-005~US-007; FR-11, FR-20, FR-22~FR-24

## SPEC Reference

`specs/RIP-011-evidence-bound-jd-matching/spec.md` - Sections 6.1~6.2, 6.5, 10
