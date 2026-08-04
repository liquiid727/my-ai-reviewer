# [RIP-007] JD library schema and domain contracts

## Description

Extend the existing JD aggregate with persistent source, processing, provenance, duplicate, ownership and update metadata required by the JD library.

## Acceptance Criteria
- [ ] Add all RIP-007 columns, checks, FKs and indexes from SPEC 3.1~3.2 to `JobDescriptionModel`
- [ ] Add JD source/status/processing-step enums and request/response domain schemas
- [ ] Alembic migration targets the actual current head and backfills legacy JD rows as `text/ready/done`
- [ ] Legacy `raw_text` remains non-null and file/URL records use an empty value only before source extraction
- [ ] Migration upgrade and downgrade tests pass
- [ ] Ruff and mypy pass for changed backend modules

## Dependencies

None

## Type

backend / database

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-001; FR-7, FR-8, FR-14

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 3.1~3.4

