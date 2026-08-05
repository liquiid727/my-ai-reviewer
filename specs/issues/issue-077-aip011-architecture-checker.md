# [AIP-011] Harden dependency checker and add exception registry

Extend the baseline AIP-010 architecture gate across static/local imports and reject broad or expired exceptions before boundary migrations begin.

## Acceptance Criteria
- [x] Checker extends the AIP-010 baseline across Domain, API, Application, Infrastructure, Tasks, and frontend transport rules
- [x] Violations report rule ID, importer, imported module, and line
- [x] Exceptions require exact scope, owner, reason, expiry, and removal issue
- [x] Checker tests cover new files, local imports, wildcard/expired exceptions, and clean paths

- **Type:** infra
- **Priority:** high
- **Depends on:** #074
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 5, 8, 11)

- **Status:** accepted (local-reviewed)
- **Evidence:** `tests/results/20260804T085546Z-aip011-issue-077-architecture-checker-r2.json` (R2)
- **Artifacts:** `scripts/quality/arch_check.py`, `scripts/quality/arch_exceptions.toml`, `backend/tests/unit/test_arch_check.py`
- **Review:** APPROVE_WITH_NITS (R2); QA GREEN (R2)
