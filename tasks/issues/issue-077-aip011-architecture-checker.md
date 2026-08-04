# [AIP-011] Harden dependency checker and add exception registry

Extend the baseline AIP-010 architecture gate across static/local imports and reject broad or expired exceptions before boundary migrations begin.

## Acceptance Criteria
- [ ] Checker extends the AIP-010 baseline across Domain, API, Application, Infrastructure, Tasks, and frontend transport rules
- [ ] Violations report rule ID, importer, imported module, and line
- [ ] Exceptions require exact scope, owner, reason, expiry, and removal issue
- [ ] Checker tests cover new files, local imports, wildcard/expired exceptions, and clean paths

- **Type:** infra
- **Priority:** high
- **Depends on:** #074
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 5, 8, 11)
