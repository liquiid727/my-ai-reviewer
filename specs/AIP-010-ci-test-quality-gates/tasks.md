# AIP-010 Tasks

| Issue | Deliverable | Depends On | Evidence |
|---|---|---|---|
| #070 | Ruff/runtime metadata baseline recovery | AIP-009 | Ruff + targeted tests |
| #071 | Production-code mypy baseline recovery | #070 | strict mypy production report |
| #072 | Test-double and optional-dependency typing recovery | #071 | strict full mypy report |
| #073 | Builder/privacy failing-test contract recovery | #070 | targeted + full pytest |
| #074 | Shared quality scripts and Make targets | #071, #072, #073 | Make target contract tests |
| #075 | Frontend test harness and critical state tests | AIP-009 | frontend test/lint/build |
| #076 | GitHub Actions gates and activation runbook | #074, #075 | workflow validation + CI run |
