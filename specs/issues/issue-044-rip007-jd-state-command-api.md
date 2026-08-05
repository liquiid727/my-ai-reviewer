# [RIP-007] JD retry, re-extract, duplicate and protected delete APIs

## Description

Complete recovery and destructive command contracts, including downstream references and existing-ID reuse.

## Acceptance Criteria
- [ ] Failed JD retry resumes from the failed step and creates a new run id
- [ ] Ready JD re-extract defaults to preserving manual fields and accepts explicit overwrite confirmation
- [ ] Duplicate confirm resumes extraction; duplicate cancel deletes the pending record
- [ ] Delete invalidates any running worker before database removal
- [ ] File deletion removes FileModel and attempts MinIO object cleanup
- [ ] Plan-referenced JD deletion returns code 1005 after RIP-008 FK is present
- [ ] Ready JD can be passed by existing `jd_id` to matching and by preselection to plan creation
- [ ] Integration tests cover each legal/illegal state, broker failure and referenced delete

## Dependencies

- `tasks/issues/issue-043-rip007-jd-list-detail-edit-api.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-006, US-007; FR-1, FR-18~FR-20

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 4.1, 5.5~5.6, 6.2

