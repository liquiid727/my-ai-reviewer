# [AIP-009] Evidence schema and governance acceptance

Normalize quality result evidence and close the governance foundation with path, conflict, privacy, and dry-run checks.

## Acceptance Criteria
- [ ] JSON template includes refs, environment, commands, statuses, exit codes, ratchet data, decision, and evidence
- [ ] Template parses and `PASS/FAIL/BLOCKED/NOT_RUN` semantics match all QA documents
- [ ] A dry-run plan for one backend and one full-stack issue records unavailable gates honestly
- [ ] `git diff --check` and canonical-path review pass

- **Type:** qa
- **Priority:** high
- **Depends on:** #067, #068
- **SPEC:** `specs/AIP-009-quality-governance-foundation/spec.md` (Sections 11-12)
