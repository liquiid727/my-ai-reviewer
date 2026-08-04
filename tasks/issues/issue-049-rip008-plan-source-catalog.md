# [RIP-008] Eligible resume options, match freshness and Source Catalog

## Description

Build generation inputs from a ready JD, Candidate Profile, current match and user preferences without leaking identity fields.

## Acceptance Criteria
- [ ] Add paginated `GET /resume?has_profile=true` returning only eligible resume summaries
- [ ] Match service reuses only results not older than JD/Profile updated_at
- [ ] Missing or stale match invokes existing JDMatchingService and stores the new result
- [ ] Source Catalog generates stable IDs for JD/Profile/Match/Preference entries
- [ ] Candidate name, email, phone and address are excluded from Catalog and snapshot
- [ ] target date, weekly hours and supplemental background become PREF entries
- [ ] Unknown or duplicate catalog IDs are rejected
- [ ] Unit/integration tests cover fresh/stale/missing match and catalog data minimization

## Dependencies

- `tasks/issues/issue-048-rip008-plan-task-schema.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-002, US-003; FR-4~FR-10

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 2.3~2.4, 5.2

