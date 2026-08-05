# AIP-015 Tasks

| Issue | Deliverable | Depends On | Evidence |
|---|---|---|---|
| #122 | Evolve interviews into the v2 Session aggregate | #121 | migration/domain tests |
| #123 | Add Session events and Coverage projection | #122 | migration/domain tests |
| #124 | Create Sessions from approved plans and start idempotently | #119, #122, #123 | unit/integration tests |
| #125 | Add Session lifecycle control commands | #116, #124 | unit/integration tests |
| #126 | Add Session expiry, history, and timeline queries | #123, #125 | unit/integration tests |
| #127 | Build Session history and live recovery shell | #124, #126 | component/build + browser checks |
| #128 | Close Session state and compatibility acceptance | #125, #127 | end-to-end + browser evidence |
