# [RIP-013] Add constrained semantic evidence matcher

Add the LLM-backed semantic classifier as a narrow adapter that can only classify allow-listed evidence for the pure engine.

## Acceptance Criteria

- [ ] Define strict Pydantic input/output contracts and application-owned matcher interface.
- [ ] Send only bounded masked Source Catalog items through the existing LLM gateway and PrivacyGuard.
- [ ] Reject unknown evidence IDs, conflicting categories, invalid dimensions, malformed output, and prompt injection.
- [ ] Apply explicit gateway timeout and bounded schema retry without holding a database transaction.
- [ ] Persist no prompt, completion, raw provider response, API key, or unmasked resume content.
- [ ] Deterministic fake and gateway-spy tests cover success, insufficient evidence, malicious, timeout, and invalid-output branches.

- **Type:** backend
- **Priority:** high
- **Depends on:** #107
- **SPEC:** RIP-013 sections 6.2/6.4, 7.1, 8
