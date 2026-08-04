# AIP-012 Tasks

| Issue | Deliverable | Depends On | Evidence |
|---|---|---|---|
| #085 | Error taxonomy and API mapper foundation | AIP-010 | unit/API handler tests |
| #086 | Resume error/public-state migration | #085, AIP-011/#078 | resume API/pipeline tests |
| #087 | JD and Plan error migration | #085, AIP-011/#079, #080 | JD/Plan API/task tests |
| #088 | Builder error migration and frontend mapping | #085, AIP-011/#081 | API/component tests |
| #089 | Structured logging, request context, and redaction | #085 | log capture/canary tests |
| #090 | Celery and LLM correlation propagation | #089 | async/gateway tests |
| #091 | Error/observability acceptance and documentation | #086-#090 | full matrix + QA report |
