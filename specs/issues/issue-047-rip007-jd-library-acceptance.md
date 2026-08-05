# [RIP-007] JD library integration and security acceptance

## Description

Close RIP-007 with end-to-end evidence across migrations, worker/API boundaries, security cases and visible user states.

## Acceptance Criteria
- [ ] Alembic, backend unit/integration, ruff, changed-module mypy, frontend lint and build pass
- [ ] Regression tests confirm existing JD matching and synchronous JD creation still work
- [ ] Browser flow covers all three imports, polling, duplicate decision, edit persistence, retry and re-extract
- [ ] SSRF suite includes IPv4/IPv6 and redirect paths
- [ ] Browser screenshots verify header and page layout on desktop/mobile without overlap
- [ ] Update relevant design/database documentation and record test evidence under project conventions
- [ ] `git diff --check` passes for delivery files

## Dependencies

- `tasks/issues/issue-046-rip007-jd-detail-ui.md`

## Type

fullstack / test

## Priority

medium

## PRD Reference

`tasks/prd-jd-library.md` - All RIP-007 stories and success metrics

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 9 and 10.3

