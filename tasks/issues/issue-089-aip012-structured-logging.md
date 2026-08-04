# [AIP-012] Add structured logging, request context, and redaction

Create one logging configuration with stable events, request/resource context, local/structured formats, and an output redaction guard.

## Acceptance Criteria
- [ ] Application startup configures logging once and libraries do not call global basic configuration
- [ ] Request ID is validated/generated at ingress and returned to the caller
- [ ] Events use allow-listed fields and appropriate levels with one owning stack trace
- [ ] Secrets, PII, prompts, completions, resumes, replacements, and unsafe exception payloads are redacted or rejected

- **Type:** backend
- **Priority:** high
- **Depends on:** #085
- **SPEC:** `specs/AIP-012-error-observability/spec.md` (Sections 5, 7-8, 11)
