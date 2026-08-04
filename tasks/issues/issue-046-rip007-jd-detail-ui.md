# [RIP-007] JD detail editor and recovery UI

## Description

Provide a traceable original-vs-structured detail experience with safe edit, retry, re-extract, delete and downstream commands.

## Acceptance Criteria
- [ ] Add `/jobs/:id` detail route showing raw text, structured fields, evidence and source/provenance
- [ ] User can edit all PRD fields; cancel produces no request
- [ ] Save success survives refresh; save failure preserves local edits
- [ ] Revision conflict reloads or offers reconciliation instead of silently overwriting
- [ ] Failed records show reason and retry; ready records show re-extract confirmation
- [ ] Delete confirmation handles referenced conflict without removing the UI record
- [ ] Ready records expose a working match entry; plan action is only rendered after RIP-008 registers its destination route
- [ ] Processing, duplicate, ready and failed states do not resize or overlap core layout
- [ ] Chinese/English copy, frontend lint and typecheck pass
- [ ] Verify desktop/mobile and the second edit interaction in a browser

## Dependencies

- `tasks/issues/issue-044-rip007-jd-state-command-api.md`
- `tasks/issues/issue-045-rip007-jd-list-import-ui.md`

## Type

frontend / ui

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-005~US-007; FR-13, FR-14, FR-18~FR-20

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 5.3, 8.3, 9.3

