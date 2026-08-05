# [RIP-007] JD list, detail and edit APIs

## Description

Expose persistent JD list/detail/edit contracts with paging, filters, lightweight rows and conflict-safe manual correction.

## Acceptance Criteria
- [ ] `GET /jd` supports page/page_size, q, source_type, status and updated_at direction
- [ ] List query selects lightweight fields and does not load raw_text or relationship collections
- [ ] `GET /jd/{id}` returns source metadata, state, raw text, structured fields and field sources
- [ ] `PATCH /jd/{id}` uses `model_fields_set` and `expected_updated_at`
- [ ] Edited fields are marked manual and explicit field clearing follows the SPEC contract
- [ ] Concurrent edit returns code 1003 without overwriting persisted data
- [ ] Existing `POST /jd`, `GET /jd/{id}` consumers and `/jd/match` remain compatible
- [ ] Integration tests cover pagination, filters, empty pages, detail, edit, clear and conflict

## Dependencies

- `tasks/issues/issue-042-rip007-jd-processing-pipeline.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-003, US-005; FR-1, FR-13, FR-15

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 4.1~4.5, 5.3

