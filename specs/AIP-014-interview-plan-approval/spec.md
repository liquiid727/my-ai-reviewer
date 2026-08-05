# AIP-014 Interview Plan Approval

> Derived from `spec-draft/interview-plan-scenarios-2026-08-05.md`, RIP-013, and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-014 |
| Title | Interview Plan Approval |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | AIP-013, RIP-013, RIP-014 |
| Prerequisites | active Job Target; immutable input versions; completed Match Assessment; scenario registry; LLM gateway/PrivacyGuard; corrected Celery runtime |

## 2. Goal

Generate a version-pinned Interview Plan, expose its public strategy and coverage for review while withholding private questions/rubrics, and require an explicit revision-safe approval before a Session can be created.

## 3. Why This Exists

AIP-001 creates a Session directly from mutable input and question count. The user cannot see what the interview will cover or control scenario, time, difficulty, and language. Generating questions only after start also blurs strategy generation with runtime recovery.

Interview Plan is a separate aggregate that freezes exact inputs and private execution material before Session creation. Its transport shape intentionally cannot serialize private plan fields.

## 4. Out of Scope

- Running questions, accepting answers, pause/resume, evaluation, or reports.
- Letting users view/edit/reorder exact questions, expected signals, or scoring rubrics.
- User-defined scenarios, custom prompt text, question-bank RAG, company research, or web search.
- Voice/video/Sandbox modes or sessions without both immutable input versions.
- Mutating a completed Match Assessment or blocking plan generation for low score.

## 5. Deliverables

- `InterviewPlan` domain/state contracts and immutable approved snapshot.
- Plan/Coverage schemas with separate public and private persistence/DTOs.
- Constrained plan generator using exact versions, assessment evidence, and scenario fixture.
- Async create/retry and revision-checked approve/reject/regenerate commands.
- Plan list/detail API and create/review frontend routes.
- Privacy, unknown-evidence, hidden-field, stale-run, conflict, and browser acceptance.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #117 | Interview Plan schema, state machine and migration | Plan US-001/005/006 | #111, #116 |
| #118 | Plan Source Catalog and constrained generator | Plan US-003/004 | #107, #117 |
| #119 | Create/query/retry/approve/reject/regenerate worker/API | Plan US-001/005/006 | #118 |
| #120 | Plan creation and public review frontend | Plan US-001/002/005/006/007 | #114, #116, #119 |
| #121 | Plan privacy, concurrency and browser acceptance | All Plan stories | #120 |

## 6. Domain

### 6.1 Plan Identity And State

Every row records Job Target, JD Version, Resume Version, Match Assessment, scenario key/version, duration, difficulty, language, run ID, revision, generation metadata, and optional `supersedes_plan_id`.

State is `generating`, `needs_review`, `approved`, `rejected`, `failed`, or `superseded`.

- Create requires a completed assessment for the exact version tuple but ignores its score as a gate.
- Approved is terminal and immutable.
- Retry reuses a failed unapproved row with a new run ID.
- Regenerate creates a new `generating` row and marks the old unapproved row superseded in one transaction.
- Reject records decision metadata but does not delete the generated plan.
- Approve/reject/regenerate require `expected_revision`.

### 6.2 Public Strategy

Public fields include scenario/config, ordered stages, stage objectives, competencies, high-level risk focus, Coverage Matrix summaries, main/follow-up budgets, expected duration, and warnings about stale current defaults.

### 6.3 Private Plan

Private fields include exact planned question text/seeds, expected signals, rubrics, evidence IDs, follow-up triggers, and internal prompt policy. They are persisted in `private_plan` and are absent from public Pydantic/TypeScript types and serializers.

### 6.4 Coverage Matrix

Each item has stable key, source type/id, category, public label, importance `1-5`, evidence sufficiency, target stages, planned main-question count, and private evidence IDs. High-importance JD requirements and high-risk Match gaps must be covered unless the selected duration cannot fit them; omissions require a public safe reason.

Question budgets come only from the exact AIP-013 fixture. Planned questions may cite only input Source Catalog IDs. Unknown IDs or coverage outside the scenario policy invalidate generation.

## 7. Application

### 7.1 Create/Generate

1. Validate target/version/assessment tuple and scenario/config.
2. Persist `generating` plan with run ID and dispatch after commit.
3. Worker loads immutable snapshots and registry fixture, builds a bounded Source Catalog, and calls the plan generator outside a transaction.
4. Validate schema, evidence allow-list, budgets, stage weights, coverage, and hidden/public separation.
5. Finalizer locks plan and verifies run/status before writing `public_strategy`, `private_plan`, and `needs_review`.

### 7.2 Decisions

Approve stores `approved_at`, approver scope `local`, scenario/config/input/private snapshot hashes, and increments revision. A later default-version update only makes the plan advisory-stale; it cannot alter or invalidate approval.

Regenerate validates old revision, creates a linked plan with a new run, and marks the old row superseded. If dispatch fails, the new row is failed and the previous row remains readable.

### 7.3 Errors

| Error code | HTTP | Meaning |
|---|---:|---|
| `PLAN_INPUT_SCOPE_MISMATCH` | 422 | Versions/assessment/target do not form one tuple |
| `PLAN_SCENARIO_INVALID` | 422 | Scenario/config unsupported |
| `PLAN_EVIDENCE_INVALID` | 502 | Generator cites unknown evidence |
| `PLAN_BUDGET_INVALID` | 502 | Generated stages/questions exceed fixture |
| `PLAN_REVISION_CONFLICT` | 409 | Decision used stale revision |
| `PLAN_ALREADY_APPROVED` | 409 | Terminal approved plan cannot be changed |
| `PLAN_DEPENDENCY_TIMEOUT` | 504 | Bounded generator timeout |
| `PRIVACY_REJECTED` | 422 | Resume-derived prompt failed closed |

## 8. Repository

Expected areas:

```text
backend/domain/interview_plan/                  [NEW]
backend/application/interview_plan/             [NEW]
backend/infrastructure/planners/interview_plan_generator.py [NEW]
backend/tasks/interview_plan_tasks.py           [NEW]
backend/api/v1/interview_plans.py               [NEW]
backend/infrastructure/db/                      [MODIFY]
infra/alembic/versions/<revision>.py             [NEW]
frontend/src/api/interview-plans.ts             [NEW]
frontend/src/types/interview-plans.ts           [NEW: public types only]
frontend/src/pages/InterviewPlanCreatePage.tsx  [NEW]
frontend/src/pages/InterviewPlanReviewPage.tsx  [NEW]
frontend/src/components/interview-plan/         [NEW]
```

Transport serializers are constructed from explicit public schemas and never `model_dump()` the ORM row/private JSON. Tests assert private-key canaries are absent from every API response.

## 9. API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/interview-plans` | Create async plan |
| GET | `/api/v1/interview-plans` | Cursor list by target/status/scenario |
| GET | `/api/v1/interview-plans/{id}` | Public plan/status only |
| POST | `/api/v1/interview-plans/{id}/retry` | Retry failed generation |
| POST | `/api/v1/interview-plans/{id}/approve` | Revision-safe approval |
| POST | `/api/v1/interview-plans/{id}/reject` | Revision-safe rejection |
| POST | `/api/v1/interview-plans/{id}/regenerate` | Create linked replacement plan |

Create request:

```json
{
  "job_target_id": "uuid",
  "jd_version_id": "uuid",
  "resume_version_id": "uuid",
  "match_assessment_id": "uuid",
  "scenario_key": "technical_first",
  "duration_minutes": 45,
  "difficulty": "standard",
  "language": "zh-CN"
}
```

Create returns 202. Decision requests carry `expected_revision`; reject may include an allow-listed reason code, not free-form prompt content. Public detail includes `can_approve/can_regenerate/can_create_session` action flags and safe failure data.

## 10. Database Impact

Create `interview_plans` with UUID primary key; indexed restrictive FKs to target, input versions, and assessment; nullable self-FK `supersedes_plan_id`; scenario/config fields; status/run/revision; `public_strategy` and `private_plan` JSONB; snapshot/content hashes; safe error fields; generation/decision/model/prompt/schema timestamps and metadata.

Constraints validate status, duration, difficulty, language, positive revision, and state-required timestamps. Indexes cover:

- `(job_target_id,created_at DESC,id DESC)`;
- `(status,updated_at)` partial for generating rows;
- each FK;
- `supersedes_plan_id`;
- optional partial index for review queue under the current anonymous scope.

No JSONB index is added. Plan queries filter relational fields and load one JSON snapshot by primary key. Approved/private content uses `ON DELETE RESTRICT` downstream.

## 11. Test Plan

- Domain: state transitions, revision conflicts, approved immutability, regenerate-link semantics.
- Generator: seven scenarios, four durations, three difficulties, two languages, budget/coverage/evidence validation.
- Privacy: gateway input is masked and public serializers never contain private question/rubric canaries.
- Worker: broker failure, timeout, retry, stale run, invalid structured output, regenerate dispatch failure.
- API: tuple mismatch, low-score eligibility, approve idempotency/conflict, reject, regenerate, stale advisory.
- Frontend/browser: all entry points, selectors, polling cleanup, public review, hidden content, approve/reject/regenerate, desktop/mobile states.
- Migration/query: constraints/FKs/indexes and bounded list query count.

PRD mapping: all Interview Plan US-001 through US-007 and FR-1 through FR-28.

## 12. Definition of Done

- [ ] Plans are generated only from one valid exact version/assessment/scenario tuple.
- [ ] Public and private schemas are separated at domain, persistence, API, frontend, and test boundaries.
- [ ] Scenario budgets, coverage, evidence, and low-score advisory behavior are enforced.
- [ ] Approval/rejection/regeneration are revision-safe and preserve history.
- [ ] Approved Plan snapshots are immutable and expose a Session-create capability without creating a Session automatically.
- [ ] Async failure/stale-worker/privacy behavior is durable and tested.
- [ ] Migration, backend, frontend, browser, lint, type, and privacy gates pass.
