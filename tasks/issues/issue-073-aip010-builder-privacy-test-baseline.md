# [AIP-010] Reconcile Builder and privacy failing-test contracts

Resolve the four behavior failures identified by the architecture review and lock the approved privacy/Builder behavior with focused tests.

## Acceptance Criteria
- [ ] Photo rendering and Builder identity behavior match the approved RIP-009/RIP-004 contracts
- [ ] The four reviewed failures pass without deleting tests or weakening assertions
- [ ] Empty, failure, optional-imaging, and masked-identity branches are covered
- [ ] Targeted suites and the complete backend pytest suite pass

- **Type:** backend
- **Priority:** high
- **Depends on:** #070
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 3, 11)
