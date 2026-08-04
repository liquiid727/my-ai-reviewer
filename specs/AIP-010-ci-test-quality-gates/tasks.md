# AIP-010 Tasks

| Issue | Deliverable | Depends On | Evidence |
|---|---|---|---|
| #070 | Ruff/runtime metadata baseline recovery | AIP-009 | PASS 2026-08-04: ruff check+format green; requires-python>=3.12; unit 210 passed; `tests/results/20260804-aip010-issue-070-ruff-runtime.json` |
| #071 | Production-code mypy baseline recovery | #070 | PASS 2026-08-04: prod mypy 0 errors (161 files); full backend 203 test-only; `tests/results/20260804T070313Z-aip010-issue-071-production-mypy.json` |
| #072 | Test-double and optional-dependency typing recovery | #071 | PASS 2026-08-04: full mypy 0 errors (206 files, tests included); unit subset 158 passed; `tests/results/20260804T071811Z-aip010-issue-072-test-mypy.json` |
| #073 | Builder/privacy failing-test contract recovery | #070 | PASS 2026-08-04: preserve confirmed photo + RIP-009 export no-auto-load; targeted 40 + full 240 passed; `tests/results/20260804T073022Z-aip010-issue-073-builder-privacy-test-baseline.json` |
| #074 | Shared quality scripts and Make targets | #071, #072, #073 | PASS 2026-08-04: scripts/quality/* + Make lint/type/arch/test-*/build/ci-fast/ci; contract 10 passed; unit 228 + integration 30; `tests/results/20260804T075308Z-aip010-issue-074-make-quality-targets.json` |
| #075 | Frontend test harness and critical state tests | AIP-009 | PASS 2026-08-04: vitest+RTL harness; 32 tests (upload/privacy, builder save/conflict, polling ownership); lint+tsc+build green; `tests/results/20260804T080921Z-aip010-issue-075-frontend-test-harness.json` |
| #076 | GitHub Actions gates and activation runbook | #074, #075 | PASS 2026-08-04: quality/test/build workflows + six stable checks + branch-protection runbook; contract tests; `tests/results/20260804T083600Z-aip010-issue-076-github-quality-workflow-r2.json` |
