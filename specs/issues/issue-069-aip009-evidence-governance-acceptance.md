# [AIP-009] Evidence schema and governance acceptance

Normalize quality result evidence and close the governance foundation with path, conflict, privacy, and dry-run checks.

## Acceptance Criteria
- [x] JSON template includes refs, environment, commands, statuses, exit codes, ratchet data, decision, and evidence
- [x] Template parses and `PASS/FAIL/BLOCKED/NOT_RUN` semantics match all QA documents
- [x] A dry-run plan for one backend and one full-stack issue records unavailable gates honestly
- [x] `git diff --check` and canonical-path review pass

- **Type:** qa
- **Priority:** high
- **Depends on:** #067, #068
- **SPEC:** `specs/AIP-009-quality-governance-foundation/spec.md` (Sections 11-12)
- **Status:** accepted (local-reviewed)
- **Evidence:** `tests/_template/quality-gate-result.template.json`, `tests/results/*-aip009-dryrun.json`, `reviews/AIP-009/governance-acceptance-2026-08-04.md`; NOT_RUN vocab normalized; Reviewer APPROVE + QA after fix 2026-08-04
