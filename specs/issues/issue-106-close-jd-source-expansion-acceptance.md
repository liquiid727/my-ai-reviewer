# [RIP-012] Close JD source-expansion acceptance

Verify all five sources share one duplicate, review, publish, archive, storage, and recovery contract.

## Acceptance Criteria

- [ ] Complete all five source flows through a published JD Version using synthetic inputs.
- [ ] Confirm image uses the existing OCR module and manual mode makes no LLM call.
- [ ] Verify file/object retention and cleanup across duplicate cancel, failure, retry, archive, and stale work.
- [ ] Verify no import mode creates a Job Target before a downstream action.
- [ ] Run migration, backend, frontend, browser, privacy, lint, type, build, and diff gates.
- [ ] Record requirement/test evidence and any environmental blocker accurately.

- **Type:** fullstack / test
- **Priority:** medium
- **Depends on:** #105
- **SPEC:** RIP-012 sections 10 through 12
