# AIP-011 Test Contract

| Requirement | Verification |
|---|---|
| Dependency direction | scan static and local imports; reject expired/wildcard exceptions |
| Behavior preservation | run characterization and API contract tests before/after each slice |
| Transaction/status ownership | simulate success, dependency error, retry, stale run/revision, conflict |
| Privacy preservation | gateway/storage spies prove masked-only and no new persistence path |
| ORM compatibility | import all metadata, Alembic current/upgrade smoke, zero unexpected schema diff |
| Frontend split | loading/empty/success/failure/pending/conflict plus export/browser path |
| Real decoupling | compare forbidden edges, dependencies, duplicate logic, and test setup cost |
