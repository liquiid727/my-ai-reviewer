# AIP-015 Interview Session State And Events

> Derived from `spec-draft/interview-runtime-report-2026-08-05.md`, AIP-001, and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-015 |
| Title | Interview Session State And Events |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | AIP-001, AIP-014, RIP-009 |
| Prerequisites | approved Interview Plan; existing `interviews` aggregate and LangGraph checkpointer; PrivacyGuard; corrected Celery runtime |

## 2. Goal

Establish the recoverable Interview Session aggregate, state/revision/idempotency rules, monotonic allow-listed events, plan coverage projection, lifecycle commands, expiry behavior, compatibility strategy, and initial frontend recovery/history shell.

## 3. Why This Exists

The current AIP-001 row supports a linear pending/generating/in-progress/report/completed flow and relies heavily on checkpoint state. It cannot safely represent an approved plan, pause/resume, concurrent tabs, idempotent commands, skip/cancel/terminate, expiry, or an auditable state projection.

Creating a second session table would duplicate the existing aggregate and complicate history. This slice evolves `interviews` in place, names it Interview Session in the new domain, and distinguishes legacy/new contracts explicitly.

## 4. Out of Scope

- Answer evaluation, coverage-based next-question selection, or follow-up generation; AIP-016 owns turn execution.
- Final report aggregation, recommendation application, and completed report UI; AIP-017 owns them.
- Backfilling incomplete legacy transcripts into new events or evaluations.
- WebSocket delivery, distributed Session services, RAG, voice/video, or Sandbox.
- Removing `/api/v1/interview` or its immediate-feedback legacy response.

## 5. Deliverables

- Version-2 Interview Session domain/state/command/query schemas.
- Migration extending `interviews`, `interview_questions`, and `question_answers`, plus new session coverage/events tables.
- Approved-plan Session creation with one-non-cancelled uniqueness.
- Idempotent start and revision-safe pause/resume/skip/cancel/terminate commands.
- 30-day inactivity expiry and watchdog/query reconciliation.
- Monotonic event transaction and safe read-only timeline projection.
- New Session resource API and frontend list/live recovery shell.
- Explicit v1/v2 compatibility and migration tests.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #122 | Session root schema, state domain and legacy compatibility migration | Runtime US-001/005 | #121 |
| #123 | Event and Session Coverage persistence/projection | Runtime US-007 | #122 |
| #124 | Approved-plan Session create and idempotent start API | Runtime US-001 | #119, #122, #123 |
| #125 | Pause/resume/skip/cancel/terminate lifecycle commands | Runtime US-005/006 | #116, #124 |
| #126 | Expiry watchdog, list/detail/timeline queries | Runtime US-005/006/010 | #123, #125 |
| #127 | Session list and live recovery shell frontend | Runtime US-001/005/010 | #124, #126 |
| #128 | Session state, concurrency, migration and browser acceptance | Runtime US-001/005/006/007/010 | #125, #127 |

## 6. Domain

### 6.1 Session Identity

A new Session is an `interviews` row with `contract_version=2` and an approved `interview_plan_id`. The Session copies exact target/version/scenario/config/hash references from the approved plan. Callers cannot override them.

A partial unique constraint allows at most one Session whose status is not `cancelled` for a plan. Repeated create returns the existing Session; a cancelled Session permits one replacement.

### 6.2 State

Session status is `ready`, `in_progress`, `paused`, `completing`, `completed`, `terminated`, `cancelled`, `failed`, or `expired`.

`turn_status` is `ready`, `evaluating`, or `retryable`. `report_status` is `not_requested`, `generating`, `completed`, or `failed`. These orthogonal fields preserve facts such as a `terminated` Session with a completed incomplete report.

Allowed command transitions:

- create approved plan -> `ready`;
- start `ready` -> `in_progress`; repeated start returns current question/state;
- pause `in_progress` -> `paused`; during evaluating, set `pause_requested` and finalize to paused;
- resume `paused` -> `in_progress` without recreating the current question;
- skip current question only when scenario budget allows and no answer is accepted;
- cancel only from `ready`;
- terminate from `in_progress` or `paused`;
- expire `ready/in_progress/paused` after 30 days without an accepted user command;
- terminal state rejects new answers and stale worker state rewrites.

Every external command except idempotent create/start requires `expected_revision`. An accepted command increments revision exactly once.

### 6.3 Coverage Projection

Session creation copies the approved plan Coverage Matrix into `interview_session_coverage`. Plan coverage remains immutable; Session coverage tracks `unverified`, `probing`, `verified_strong`, `verified_partial`, `risk`, `skipped`, or `not_reached`, plus evidence counts and last question/evaluation references.

This Spec creates and exposes the projection. AIP-016 owns coverage-selection and evaluation updates.

### 6.4 Event Contract

Every event has Session ID, strictly increasing sequence, event type, allow-listed JSON payload, created timestamp, and optional command/run correlation IDs.

Initial types: `session.created`, `session.started`, `question.asked`, `question.skipped`, `session.paused`, `session.resumed`, `session.cancelled`, `session.terminated`, `session.expired`, `session.failed`, and later types reserved by AIP-016/017.

Payloads may contain IDs, status/stage/coverage keys, counts, safe reason/error codes, attempts, and durations. They cannot contain question/answer/evidence text, score, feedback, prompt, completion, credentials, or replacement maps.

## 7. Application

### 7.1 Module Interface

```text
InterviewSessionCommands.create_from_plan(plan_id)
InterviewSessionCommands.start(session_id)
InterviewSessionCommands.pause/resume/skip/cancel/terminate(command)
InterviewSessionCommands.retry(command)
InterviewSessionQueries.get/list/timeline(query)
InterviewSessionReconciler.expire_overdue(now)
```

Commands lock the Session root, validate state/revision, mutate state and child projection, allocate the next event sequence, and commit together. Locks are acquired root first and child rows by stable key order.

### 7.2 Start

Start loads the first allowed private planned question through the Interview Plan application interface, creates or returns one persisted public question, sets timestamps/current question, and writes `session.started` plus `question.asked`. It never returns the rest of the plan.

### 7.3 Pause, Skip, Terminate

- Pause during a ready turn is immediate. During evaluation it records `pause_requested`; duplicate pause is idempotent.
- Skip writes question status/reason and coverage `skipped`, decrements scenario allowance, and delegates next-question materialization to the runtime interface. Until AIP-016 is shipped, the feature is not enabled in the frontend release flag.
- Terminate records terminal status and, when at least one evaluated answer later exists, requests an incomplete report through AIP-017. With zero evaluated answers, `report_status` remains `not_requested`.

### 7.4 Expiry And Recovery

`expires_at` is 30 days after the latest accepted user command. Status reads lazily reconcile one overdue Session; a Celery Beat watchdog reconciles batches. Expiry does not silently restart, generate a report, or delete history. Resume reload uses relational Session/question/coverage state; checkpointer mismatch is recoverable and observable, not authoritative.

### 7.5 Errors

| Error code | HTTP | Meaning |
|---|---:|---|
| `PLAN_NOT_APPROVED` | 409 | Session creation source invalid |
| `SESSION_ALREADY_EXISTS` | 200/409 | Idempotent result includes existing ID |
| `SESSION_INVALID_STATE` | 409 | Command not allowed now |
| `SESSION_REVISION_CONFLICT` | 409 | Reload/reconcile required |
| `SESSION_EXPIRED` | 410 | New mutation rejected |
| `SESSION_SKIP_LIMIT` | 409 | Scenario skip allowance exhausted |
| `SESSION_TURN_BUSY` | 409 | Command conflicts with active turn |
| `SESSION_NOT_FOUND` | 404 | Unknown Session |

## 8. Repository

Expected areas:

```text
backend/domain/interview_session/                [NEW]
backend/application/interview_session/           [NEW]
backend/api/v1/interview_sessions.py             [NEW]
backend/tasks/interview_session_watchdog.py      [NEW]
backend/infrastructure/db/                       [MODIFY]
backend/workflow/checkpointer.py                 [MODIFY only for v2 key/repair hooks]
infra/alembic/versions/<revision>.py              [NEW]
frontend/src/api/interview-sessions.ts           [NEW]
frontend/src/types/interview-sessions.ts         [NEW]
frontend/src/pages/InterviewSessionListPage.tsx  [NEW]
frontend/src/pages/InterviewSessionPage.tsx      [NEW shell]
```

The new application module is the only owner of v2 Session mutation. Legacy `interview_service.py` and `/interview` continue to own v1 rows. Serializers dispatch by `contract_version` and never silently reinterpret a legacy row as v2.

## 9. API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/interview-sessions` | Idempotent create from approved plan |
| GET | `/api/v1/interview-sessions` | Cursor list by target/scenario/status |
| GET | `/api/v1/interview-sessions/{id}` | Recoverable public projection/current question |
| GET | `/api/v1/interview-sessions/{id}/timeline` | Allow-listed event timeline |
| POST | `/api/v1/interview-sessions/{id}/start` | Idempotent start |
| POST | `/api/v1/interview-sessions/{id}/pause` | Revision-safe pause |
| POST | `/api/v1/interview-sessions/{id}/resume` | Revision-safe resume |
| POST | `/api/v1/interview-sessions/{id}/skip` | Revision-safe allowed skip |
| POST | `/api/v1/interview-sessions/{id}/cancel` | Cancel before start |
| POST | `/api/v1/interview-sessions/{id}/terminate` | End early |
| POST | `/api/v1/interview-sessions/{id}/retry` | Retry allowed turn/report failure |

Create request is `{ "interview_plan_id": "uuid" }`. Mutation requests contain `expected_revision` and safe reason code where applicable. Public projection includes scenario, target/version summaries, status/turn/report status, revision, current question, progress counts, skip remaining, timestamps, safe failure, and action flags. It excludes private plan/evaluation fields.

## 10. Database Impact

### 10.1 Extend `interviews`

Add `contract_version` default 1 for existing rows; nullable indexed `interview_plan_id`; `revision`; `turn_status`; `report_status`; current question ID; `next_event_sequence`; `pause_requested`; start/pause/activity/expiry/finish timestamps; active elapsed seconds; safe failure step/code/retryability; current turn/report run IDs.

Add checks for v1/v2 fields and states. Add partial unique `interview_plan_id WHERE contract_version=2 AND status <> 'cancelled'`, active watchdog `(status,expires_at)` partial index, and `(updated_at DESC,id DESC)` cursor index.

### 10.2 New `interview_session_coverage`

Columns include Session FK, coverage key/category/source/importance, public label, status, evidence sufficiency/count, last question/evaluation IDs, and timestamps. Unique `(interview_id,coverage_key)`; index all FKs.

### 10.3 New `interview_events`

Columns include Session FK, positive sequence, type, payload JSONB, command/run IDs, and created timestamp. Unique `(interview_id,sequence)` plus `(interview_id,created_at,id)` index. No text-search/GIN index.

### 10.4 Extend Questions/Answers

Add question kind/status, parent question, plan stage, coverage keys, asked/skipped timestamps, generation key; add answer idempotency/status/masked contract fields required by AIP-016. Existing score/feedback/raw fields remain legacy-only and nullable for v2.

Migration sets all existing rows to contract version 1 and does not synthesize events. Downgrade is possible only before v2 rows are referenced by later AIP migrations.

## 11. Test Plan

- Domain transition table for every state/command/turn/report combination.
- Concurrent create/start/pause/resume/skip and expected-revision conflicts.
- Event sequence uniqueness, rollback atomicity, payload allow-list, projection rebuild.
- Partial unique one non-cancelled Session per approved plan.
- Expiry lazy/watchdog paths, terminal mutation rejection, stale-worker no-op.
- Migration with representative legacy AIP-001 rows and unchanged legacy API behavior.
- Query count/cursor stability for list/timeline without transcript/private-plan loads.
- Frontend/browser: deep-link refresh, pause/resume, conflict, expired, cancelled, terminated, loading/empty/failure/pending states.
- Privacy canaries absent from events, safe failures, responses, screenshots, and logs.

PRD mapping: Runtime US-001, US-005, US-006, US-007, US-010 and FR-1 through FR-5, FR-18 through FR-28, FR-35/36.

## 12. Definition of Done

- [ ] New Sessions originate only from approved plans and preserve exact snapshot references.
- [ ] Create/start are idempotent; every racing mutation is revision-safe.
- [ ] Session, turn, and report states retain distinct business facts.
- [ ] State and events commit atomically with monotonic, content-safe payloads.
- [ ] Relational state can restore the current question/progress without relying solely on a checkpoint.
- [ ] Expiry, terminal-state, skip, stale-worker, and compatibility behavior are fully tested.
- [ ] Legacy AIP-001 rows/routes remain unchanged and explicitly versioned.
- [ ] Migration, backend, frontend, browser, privacy, lint, type, and query gates pass.
