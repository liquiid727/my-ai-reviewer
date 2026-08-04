# [RIP-007] Text and file JD import service

## Description

Implement text/file ingestion, validation, MinIO ownership and existing parser reuse while returning a processing JD immediately.

## Acceptance Criteria
- [ ] Add `/jd/import/text` and `/jd/import/file` request handling through `JDImportService`
- [ ] Enforce verified LLM gate before import dispatch
- [ ] Text accepts 1~100000 trimmed characters
- [ ] File accepts PDF/DOCX/TXT/MD only and rejects content above 10MB
- [ ] Store file under the existing MinIO bucket with a `jd/` prefix and `FileModel.owner_type=job_description`
- [ ] Download and parse file content with existing parser implementations
- [ ] Database or dispatch failure performs the documented object/database compensation
- [ ] Unit tests cover valid inputs, type/size failures, MinIO failure and parser failure

## Dependencies

- `tasks/issues/issue-039-rip007-jd-library-schema.md`

## Type

backend

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-002; FR-2, FR-3, FR-7

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 2.3, 4.2, 6.2

