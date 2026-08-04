# AIP-010 Test Contract

| Scenario | Expected evidence |
|---|---|
| clean backend | Ruff format/check, strict mypy, unit and integration suites pass |
| clean frontend | component tests, Oxlint, TypeScript, and production build pass |
| injected static/type/test failure | owning gate exits non-zero and aggregate identifies it |
| missing integration service | non-zero `BLOCKED` result, not silent skip/pass |
| new skip/ignore/exception | ratchet fails without owner, expiry, and removal issue |
| coverage decrease | gate fails against recorded baseline |
| local/hosted parity | Make and GitHub jobs call equivalent scripts/commands |
| evidence safety | reports/logs contain synthetic values and no secret/PII payloads |
