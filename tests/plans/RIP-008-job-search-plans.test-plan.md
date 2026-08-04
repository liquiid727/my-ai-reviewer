---
standardVersion: specos-test-standard/v1
qualityProfile: fullstack-concurrency-migration
riskTier: P1
specId: RIP-008
specVersion: 2026-08-03
featureName: AI job-search plans
source:
  - tasks/prd-job-search-plans.md
  - specs/RIP-008-job-search-plans/spec.md
  - specs/RIP-008-job-search-plans/tasks.md
flakePolicy: Retry only transport-dependent browser checks; mutation, revision, migration, and preservation checks are non-retryable.
dataPolicy: Use isolated PostgreSQL schema/database data and synthetic JD/profile/match fixtures; do not place identity fields in prompts or snapshots.
securityPolicy: Assert catalog/snapshot minimization and untrusted catalog prompt boundaries; no real provider calls in automated tests.
---

# RIP-008 Test Plan

## Flows

| Flow | Ordered stages | Scenarios |
|---|---|---|
| Create and generate | select ready JD + eligible resume -> validate -> generating -> worker -> active/failed | duplicate pair, broker failure, stale run, malformed LLM output |
| Execute plan | read detail -> autosave task mutation -> revision update -> progress/state transition | second edit, cross-task conflict, reorder, reopen/delete |
| Regenerate safely | confirm -> regenerating -> stage outside lock -> atomic replace/restore | preserve manual/done rows, failed generation, stale/delete run |
| Connected UI | JD/resume deep links -> plan create -> detail/list navigation | invalid preselection, mobile header, polling, retry |

## Endpoint Coverage

| Interface | Branches and expected result | Evidence |
|---|---|---|
| `GET /resume?has_profile=true` | only profile-backed lightweight options; no identity/raw text | `test_jd_plan_api.py::test_plan_create_duplicate_and_eligible_resume_contract` |
| `POST/GET/PATCH/DELETE /plans` | ready/profile/config validation, duplicate 1006, list aggregation, stale flag, retry/delete | `test_jd_plan_api.py` creation/dispatch/persistence/regeneration cases plus service tests |
| task CRUD/order endpoints | plan-level expected revision, 1007 conflict, 200 limit, completed/reopen/delete rules | `test_jd_plan_api.py`, `test_plan_task_service.py` |
| `/plans/{id}/regenerate` | new run, lock gate, preserve manual/done, atomic failure restore | regeneration service/API tests and browser scenario pending |

## Traceability

| PRD scope | Requirements | Issues | Automated evidence | Visual/browser evidence |
|---|---|---|---|---|
| US-001 plan/task persistence | FR-1..FR-3, FR-8, FR-9, FR-22, FR-23 | 048 | Alembic round-trip; ORM/domain contracts | pending desktop/mobile detail scenario |
| US-002 valid inputs | FR-4..FR-6 | 049, 051, 054 | eligibility and API fixtures | pending create/deep-link scenario |
| US-003 evidence-backed generation | FR-7..FR-10, FR-21 | 049..051, 056 | `test_plan_generation.py`; worker/service checks | pending generate/retry scenario |
| US-004 task execution | FR-11..FR-15 | 052, 055 | `test_plan_task_service.py`, `test_jd_plan_api.py` | pending repeated autosave/conflict scenario |
| US-005 safe regeneration | FR-16..FR-19 | 053, 056 | regeneration preservation/failure checks | pending confirm/failure scenario |
| US-006 plan list | FR-1, FR-20 | 051, 054 | API list/detail aggregation assertions | pending list/filter state scenario |
| US-007 connected entry points | FR-2, FR-3 | 046, 054, 057 | route/client build checks | pending JD/resume deep-link scenario |

## Scope Boundary

`TODO-PLAN-001` through `TODO-PLAN-008` are excluded from all flows, endpoints, and source paths. A delivery scan must return no implementation references under `backend/`, `frontend/`, or `infra/`.

## Production Gates

| Requirement ID | Layer | Applies to | Required evidence | Gate impact |
|---|---|---|---|---|
| RIP8-MIGRATION | migration | 048, 057 | upgrade -> downgrade -> upgrade on isolated PostgreSQL database | blocking |
| RIP8-GENERATION | unit/API | 049..051 | catalog minimization, schema validation, stale/duplicate handling | blocking |
| RIP8-CONCURRENCY | unit/integration | 052, 053, 055 | expected-revision, serialization, preservation, failure atomicity | blocking |
| RIP8-UI | lint/build/browser | 054..057 | lint/build plus deep-link/interaction desktop/mobile screenshots | blocking until browser evidence exists |
