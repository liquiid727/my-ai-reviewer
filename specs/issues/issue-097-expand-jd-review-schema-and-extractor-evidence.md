# [RIP-011] Expand JD review schema and extractor evidence

Extend JD structured extraction to the complete review schema with stable evidence, confidence, provenance, and strict output validation.

## Acceptance Criteria

- [ ] Add all scalar/list/hard-condition fields defined by the JD PRD with bounded Pydantic v2 schemas.
- [ ] Give requirements/responsibilities/skills stable item keys, evidence status, confidence, and provenance.
- [ ] Return null/empty for unknown fields and reject fabricated/unknown evidence references.
- [ ] Save parser/model/prompt/schema versions and overall confidence without raw provider output.
- [ ] Treat embedded source instructions as untrusted data.
- [ ] Synthetic complete/sparse/conflicting/malicious/malformed fixtures pass.

- **Type:** backend
- **Priority:** high
- **Depends on:** #094
- **SPEC:** RIP-011 sections 6.1, 7.1, 11
