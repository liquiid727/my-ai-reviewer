# AIP-010 CI And Test Quality Gates

> Derived from `spec-draft/engineering-quality-governance-2026-08-04.md` and AIP-009
> Generated: 2026-08-04 | Target branch: `main` | Base commit: `89c87f6`

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-010 |
| Title | CI And Test Quality Gates |
| Epic | Engineering Quality Governance |
| Status | Proposed |
| Owner Agent | CI Agent |
| Depends On | AIP-009 |
| Prerequisites | quality gate rules, backend uv lock, frontend pnpm lock, synthetic test data |

## 2. Goal

Restore a green quality baseline and provide deterministic local and GitHub CI gates for lint, formatting, typing, architecture, backend/frontend tests, integration prerequisites, coverage, and builds.

## 3. Why This Exists

At the source review the backend had 14 Ruff findings, 45 mypy errors, and 4 failing tests. `make lint` and `make test` exist, but there is no `make ci`, format/type/architecture target, frontend test command, or hosted workflow. Turning on a red gate without baseline recovery would normalize bypasses rather than improve quality.

## 4. Out of Scope

- Business feature changes unrelated to restoring documented behavior.
- Architecture migration beyond the executable dependency checker introduced for AIP-011.
- Production deployment, release automation, or unapproved branch-protection mutation.
- An arbitrary repository-wide coverage percentage before measurement.

## 5. Deliverables

- Zero-error Ruff and strict mypy baseline aligned to Python 3.12.
- Current Builder/privacy test contract reconciled and backend suite green.
- Frontend unit/component test harness and critical workflow tests.
- Shared, read-only quality scripts and stable Make targets defined by `rules/quality-gates.md`.
- GitHub Actions jobs with PostgreSQL/Redis prerequisites, lockfile installs, artifacts, and stable check names.
- Coverage/skip baseline and ratchet with dated exceptions only.

## 6. Domain

Each `GateResult` contains gate ID, exact command, status, exit code, duration, summary, evidence, and baseline/new/resolved counts. Required integration tests distinguish environmental `BLOCKED` from behavioral `FAIL`. A gate cannot mutate source files.

## 7. Application

Local Make targets and hosted jobs call the same scripts/commands. Fast gates run first; unit, integration, frontend, and build jobs remain separately visible. The aggregate target exits non-zero on any required failure and preserves individual logs. Coverage ratchets reject decreases and critical-path gaps.

## 8. Repository

Expected implementation areas:

- `Makefile` stable target surface;
- `scripts/quality/` shared gate runners and architecture check entry point;
- `backend/pyproject.toml` tool/runtime alignment;
- `frontend/package.json` test/type scripts and test configuration;
- `.github/workflows/quality.yml` hosted gates;
- `tests/results/` normalized evidence and feature test contracts.

Quality scripts are source; coverage/build/report output is generated and not committed unless the evidence rule explicitly requires a normalized summary.

## 9. API

None. Existing API behavior may be exercised by integration tests but no endpoint is added.

## 10. Database Impact

None. CI uses an isolated synthetic test database and never production data. Migration smoke uses existing Alembic metadata.

## 11. Test Plan

- Prove every Make target is read-only, returns the underlying failure code, and works from repository root.
- Seed one controlled failure per gate in isolated fixtures or script tests and confirm it blocks.
- Verify DB-unavailable integration runs report `BLOCKED`/non-zero rather than a false pass.
- Verify GitHub jobs use Python 3.12, lockfiles, synthetic secrets/data, and stable names.
- Establish coverage and skip baselines; verify a decrease/new unexplained skip fails.
- Run full `make ci`, `git diff --check`, backend suite, frontend test/lint/build, and migration smoke when services are available.

## 12. Definition of Done

- [ ] Ruff, format check, strict mypy, backend unit/integration, frontend test/lint/build, and architecture gate are reproducible locally.
- [ ] Current source-review failures are resolved without ignores, removed tests, or weakened assertions.
- [ ] `make lint`, `make type-check`, `make arch-check`, `make test-*`, `make ci-fast`, and `make ci` match documented semantics.
- [ ] Hosted jobs call equivalent commands and publish safe evidence.
- [ ] Coverage and skip ratchets are measured, documented, and non-decreasing.
- [ ] Branch-protection activation remains a separately authorized delivery action.
