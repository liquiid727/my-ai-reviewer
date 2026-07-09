# EnterpriseSpec

`EnterpriseSpec` is the governed operating mode for this project.

Use it when:

- QA evidence must be complete
- release, rollout, and rollback records are required
- security, performance, or compliance reviews are mandatory
- multiple teams need role-based context loading

Core shape:

```text
project/
  README.md
  docs/spec-modes/
  current/
  design/
  specs/
  implementation/
  tests/
  reviews/
  docs/
  .agents/
```

Recommended role-based loading:

- architecture: `design/`, `specs/`, `reviews/architecture/`
- implementation: `current/`, `specs/`, `implementation/`
- QA: `specs/`, `tests/`, `reviews/`
- security: `design/security.md`, `tests/security/`, `reviews/security/`
- release: `implementation/`, `reviews/release/`, `docs/runbook/`
