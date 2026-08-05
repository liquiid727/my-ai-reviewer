# [RIP-012] Add manual JD source creation

Add synchronous structured manual JD creation with honest provenance and mandatory review before publish.

## Acceptance Criteria

- [ ] Add `manual` source policy and request schema with title as the only mandatory business field.
- [ ] Validate all optional fields against RIP-011 bounds and canonical structured shape.
- [ ] Persist manual provenance/confidence without fabricating source quotes or calling an LLM.
- [ ] Enter `needs_review`, never auto-publish, and never create a Job Target.
- [ ] Apply canonical duplicate detection and existing archive/reference rules.
- [ ] API/domain tests cover sparse/complete/invalid/duplicate manual entries.

- **Type:** backend
- **Priority:** medium
- **Depends on:** #102
- **SPEC:** RIP-012 sections 6.2/6.3, 7.1, 9
