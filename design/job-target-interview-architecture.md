# Job Target Interview Architecture

**Status**: Proposed target design, pending Spec review

**Prepared**: 2026-08-05

**Sources**:

- `spec-draft/job-target-interview-program-2026-08-05.md`
- `spec-draft/jd-import-library-2026-08-05.md`
- `spec-draft/resume-jd-match-assessment-2026-08-05.md`
- `spec-draft/interview-plan-scenarios-2026-08-05.md`
- `spec-draft/interview-runtime-report-2026-08-05.md`

## 1. Architectural Decision

The Job Target interview program extends the existing React/FastAPI/Celery modular monolith. It does not create microservices, a second JD library, a second preparation-task store, or a free-running multi-agent network.

The target flow is:

```text
JD identity + review draft -> immutable JD Version
parsed resume / Builder revision -> immutable masked Resume Version
                                |
                                v
                         active Job Target
                                |
                                v
                 version-pinned Match Assessment
                                |
                                v
                generated and approved Interview Plan
                                |
                                v
              recoverable plan-driven Interview Session
                                |
                                v
             evidence-backed Report -> explicit RIP-008 tasks
```

The design adds append-only snapshots around mutable authoring resources. Existing `job_descriptions`, parsed resumes, Builder drafts, and `interviews` remain the implementation base. New consumers use exact version IDs and new resource APIs; legacy APIs remain available during a measured compatibility period.

## 2. Contexts And Ownership

| Context | Owned concepts | Existing implementation reused | New canonical module interface |
|---|---|---|---|
| JD Catalog | JD identity, import source, review draft, JD Version | RIP-003/RIP-007, parser factory, SafeWebFetcher, JDExtractor, MinIO | import source, save review, publish version, version queries, archive |
| Candidate Snapshot | Resume Version | RIP-002/RIP-004/RIP-009, Candidate Profile, Builder revision, PrivacyGuard | publish or resolve an immutable masked version |
| Career Target | Job Target, Match Assessment | RIP-003 matching rules, RIP-008 source catalog concepts | ensure target, select defaults, create/retry/query assessment |
| Interview Planning | Interview Scenario, Interview Plan, Coverage Matrix | AIP-001 interview schemas, LLM gateway | list scenarios, create plan, approve/reject/regenerate |
| Interview Execution | Interview Session, Question, Answer, Answer Evaluation, Session Event | AIP-001 LangGraph, agents, checkpointer, report worker | create/start/answer/control/query session |
| Preparation Plan | selected report recommendation handoff | RIP-008 task commands and revision control | existing manual-task command; no direct table mutation |

Each context is a deep module: callers use resource commands and queries without learning persistence, prompt, worker, checkpoint, or provider details. The existing LLM gateway, parser registry, MinIO client, PrivacyGuard, and RIP-008 task command are real seams with production adapters and test replacements. No new generic repository or provider abstraction is introduced without a second concrete adapter.

## 3. Ubiquitous Language

| Term | Canonical meaning | Explicitly not |
|---|---|---|
| Job Description | Stable identity for one imported or manually entered role and its source history | A published immutable snapshot |
| JD Review Draft | Mutable extraction/review projection attached to a Job Description | A downstream-safe input |
| JD Version | Immutable published JD snapshot with evidence and generation metadata | The current mutable fields on `job_descriptions` |
| Resume Version | Immutable masked snapshot of one parsed resume state or one Builder revision | The editable resume or Builder draft |
| Job Target | Minimal active or archived workspace for one Job Description identity | An application tracker, reminder system, or recruiting pipeline |
| Match Assessment | Immutable completed evaluation of one JD Version, one Resume Version, and one scoring policy | A gate that blocks interview training |
| Interview Scenario | Code-owned, versioned policy for stages, budgets, coverage, skip, follow-up, and scoring | User-authored prompt content |
| Interview Plan | Generated strategy and private question/rubric snapshot for exact input versions | A live interview session |
| Interview Session | One execution of one approved Interview Plan | A reusable plan or mutable input selection |
| Coverage Item | One requirement, competency, or risk to verify, with importance and evidence sufficiency | A question itself |
| Answer Evaluation | Internal structured evaluation used for coverage and reporting | Feedback shown during the live session |
| Session Event | Allow-listed state-change record with a monotonic sequence | A transcript, prompt log, or raw audit payload |

The existing `interviews` row becomes the persistence root for the canonical Interview Session. The user-facing and domain term is `Interview Session`; `Interview` remains only a legacy route/table name during compatibility.

## 4. Cross-Context Invariants

1. Published JD Versions, Resume Versions, completed Match Assessments, approved Interview Plans, and generated Reports are append-only business snapshots.
2. A correction creates a new snapshot. It never mutates the meaning of a historical downstream resource.
3. A Job Target is created only by a downstream command and is idempotent per active Job Description identity.
4. Match score is advisory. Every completed assessment can be used to create an Interview Plan.
5. An Interview Session can be created only from an approved Interview Plan.
6. One approved plan can own at most one non-cancelled Session.
7. Plan review exposes public strategy and Coverage Matrix summaries, never private planned questions, expected signals, or rubrics.
8. Live-session responses never expose evaluation scores, feedback, expected signals, or rubrics.
9. Resume-derived and answer-derived LLM inputs contain masked content only and pass PrivacyGuard.
10. PostgreSQL is the business-state source of truth. LangGraph checkpoints accelerate orchestration but cannot be the only recoverable state.
11. Every worker finalizer verifies resource ID, run ID, revision, and allowed source state before writing.
12. Report recommendations enter RIP-008 only through the existing revision-checked manual-task command after explicit confirmation.

## 5. Scenario Registry

The first release uses a code-backed registry under the interview domain. There is no scenario table or admin CRUD.

| Key | Version | Stages in order | Main emphasis |
|---|---|---|---|
| `comprehensive` | `1` | introduction, core_skills, project, system_design, behavior, candidate_questions | Balanced role simulation |
| `hr_screen` | `1` | introduction, background, motivation, behavior, candidate_questions | Fit, motivation, communication |
| `technical_first` | `1` | introduction, core_skills, problem_solving, project, candidate_questions | Required skills and reasoning |
| `project_deep_dive` | `1` | introduction, project_context, project_decisions, tradeoffs, outcomes, candidate_questions | Evidence and ownership |
| `system_design` | `1` | clarification, architecture, data, scaling, reliability, tradeoffs, candidate_questions | Design decisions and constraints |
| `behavioral` | `1` | introduction, ownership, collaboration, conflict, learning, candidate_questions | STAR evidence and reflection |
| `manager_round` | `1` | introduction, prioritization, leadership, cross_functional, growth, candidate_questions | Scope, judgment, growth |

Stable configuration:

- duration: `15`, `30`, `45`, or `60` minutes;
- main-question budget: `3`, `5`, `7`, or `9` respectively;
- total follow-up budget: `1`, `3`, `5`, or `7` respectively;
- maximum follow-up depth per main question: `2`;
- candidate questions: minimum `1`, maximum `3` where the scenario includes that stage;
- difficulty: `basic`, `standard`, or `challenge`;
- language: `zh-CN` or `en`;
- skip allowance: `1` for 15/30 minutes and `2` for 45/60 minutes, further constrained by scenario fixture;
- session inactivity TTL: 30 days from the most recent accepted user command;
- incomplete report threshold: at least one successfully evaluated answer.

Scenario fixtures include stage weights that sum to 100, allowed coverage categories, main/follow-up budgets, skip allowance, scoring dimensions, and prompt policy version. Fixture validation is executable and blocks an invalid registry at application startup/test time.

## 6. Match Scoring Policy

Policy `match-v1` uses these weights:

| Dimension | Weight |
|---|---:|
| required skills | 25 |
| years and depth of experience | 15 |
| project evidence | 20 |
| responsibility alignment | 15 |
| technical stack and tools | 10 |
| industry/business context | 5 |
| basic conditions | 5 |
| preferred qualifications | 5 |

Deterministic rules evaluate explicit skills, years, education/certification, location, and other hard conditions. A constrained LLM may classify semantic evidence only from an allow-listed Source Catalog. Unknown evidence IDs invalidate the result.

The total is the weighted sum after deterministic rules. Missing a core required skill caps the total at 75. A policy-defined severe years gap caps it at 70. When multiple caps apply, the lowest cap wins. Evidence insufficiency produces `evidence_gap`, not a capability claim. The four report categories are `capability_gap`, `expression_gap`, `evidence_gap`, and `hard_constraint_risk`.

## 7. State Models

### 7.1 JD identity and review

```text
processing -> duplicate_pending -> processing
processing -> needs_review
processing -> failed -> processing (retry)
needs_review -> ready (publish immutable version)
needs_review -> processing (reparse)
ready -> processing (new review draft; current version remains usable)
any non-deleted state -> archived
```

Publishing is idempotent on `(job_description_id, content_hash, schema_version)`. `ready` means at least one published version exists. A failed reparse does not remove or replace the current version.

### 7.2 Match Assessment

```text
queued -> evaluating -> completed
queued/evaluating -> failed
failed -> queued (new run on same assessment identity)
completed -> new assessment row (explicit re-evaluate)
```

Completed assessments are immutable. A normal create command reuses the latest completed row with the same input IDs and policy version. `force=true` creates a new assessment row.

### 7.3 Interview Plan

```text
generating -> needs_review | failed
failed -> generating (new run)
needs_review -> approved | rejected | superseded
rejected/needs_review -> new generating plan linked by supersedes_plan_id
approved -> terminal plan snapshot
```

Approval, rejection, retry, and regeneration require `expected_revision`. Regeneration creates a new plan row and preserves the old row. An approved plan is never regenerated in place.

### 7.4 Interview Session

```text
ready -> in_progress -> paused -> in_progress
ready -> cancelled
in_progress/paused -> terminated
in_progress -> completing -> completed
ready/in_progress/paused -> expired
in_progress -> failed -> in_progress (retryable turn/report only)
```

`turn_status` is separate from Session status: `ready`, `evaluating`, or `retryable`. `report_status` is also separate: `not_requested`, `generating`, `completed`, or `failed`. A terminated Session can therefore receive an incomplete report without losing the `terminated` fact. Pause during `evaluating` records `pause_requested`; the worker may persist the hidden evaluation but must leave the Session paused before exposing the next turn. Terminal states cannot be reopened by stale workers.

## 8. Persistence Model

All new primary keys are UUID, timestamps are `timestamptz`, enum-like fields are text/varchar with check constraints, and every foreign-key query path has an index.

### 8.1 New tables

| Table | Purpose | Key constraints/indexes |
|---|---|---|
| `job_description_versions` | Immutable published JD snapshot | unique `(job_description_id, version_no)`; indexed FK; unique content key per JD/schema |
| `resume_versions` | Immutable masked resume/Builder snapshot | unique source revision/content key; indexed source FKs; PrivacyGuard metadata |
| `job_targets` | Minimal active/archived target workspace | partial unique `job_description_id WHERE archived_at IS NULL`; `(updated_at,id)` list index |
| `match_assessments` | Version-pinned match lifecycle and result | indexed target/version FKs; partial active-run index; `(job_target_id,created_at,id)` list index |
| `interview_plans` | Public strategy plus private approved plan snapshot | indexed target/version/assessment FKs; active-run and history indexes |
| `interview_session_coverage` | Mutable coverage projection copied from approved plan | unique `(interview_id,coverage_key)`; indexed interview FK |
| `answer_evaluations` | One structured evaluation per accepted answer | unique `answer_id`; indexed question/coverage references |
| `interview_events` | Monotonic allow-listed session events | unique `(interview_id,sequence)`; `(interview_id,created_at)` index |
| `interview_report_recommendations` | Immutable recommendation content plus idempotent apply metadata | unique `(report_id,recommendation_key)`; indexed report/plan-task FKs |

### 8.2 Extended tables

- `job_descriptions`: add `current_version_id`, `archived_at`, `review_revision`, richer draft JSON/provenance, and expanded source/state checks. Existing content columns remain the review projection during compatibility.
- `job_search_plans`: add nullable `job_target_id`, `jd_version_id`, `resume_version_id`, and `match_assessment_id`. New plan creation writes all four; legacy rows remain readable.
- `interviews`: add `contract_version`, `plan_id`, `revision`, `turn_status`, current question, activity/expiry timestamps, pause request, safe failure fields, and report run ownership.
- `interview_questions`: add question kind, parent question ID, plan stage, coverage keys, status, asked/skipped timestamps, and generation key.
- `question_answers`: add idempotency key, masked-answer contract, answer status, and accepted timestamp. New rows do not write score/feedback fields.
- `interview_reports`: add completeness, coverage summary, evidence map, policy versions, and generated timestamp. Report content remains immutable.

### 8.3 Snapshot shapes

`job_description_versions` stores normalized text, structured fields, field evidence/confidence/provenance, source metadata, content hash, parser/model/schema versions, publication reason, and published timestamp.

`resume_versions` stores source kind and source reference, source revision, content hash, masked content, Candidate Profile/evidence snapshot, parser/schema/privacy-policy versions, and published timestamp. It never stores a token-to-real-value manifest.

`interview_plans` separates `public_strategy` from `private_plan`. Only the application/workflow module can load `private_plan`; transport serializers have no field for it.

### 8.4 Transaction and locking rules

- External network, file parsing, OCR, and LLM calls run outside database transactions.
- Finalizers open short transactions, lock the root resource first, then child rows in stable UUID/order sequence.
- Optimistic commands update `WHERE id=:id AND revision=:expected_revision` and fail with conflict when no row is affected.
- Event sequence allocation locks the Session root, increments `next_event_sequence`, writes state and event in one transaction, then commits.
- Batched/JOIN projections load list summaries without per-row report, plan, or coverage queries.

## 9. HTTP Resource Design

New endpoints remain under `/api/v1` and use the existing `APIResponse {code,message,data}` envelope. Success uses transport 2xx and `code=0`. Validation uses 422; not-found 404; revision/idempotency conflict 409; expired resource 410; dependency failure 502; dependency timeout 504. Legacy routes retain their current behavior until their dedicated compatibility removal is approved.

| Resource | Commands and queries |
|---|---|
| JD versions | `GET /jd/{id}/versions`, `GET /jd/{id}/versions/{version_id}`, `POST /jd/{id}/publish`, `POST /jd/{id}/reparse`, `POST /jd/{id}/archive` |
| Resume versions | `POST /resume-versions`, `GET /resume-versions`, `GET /resume-versions/{id}` |
| Job Targets | `POST /job-targets`, `GET /job-targets`, `GET/PATCH /job-targets/{id}`, `POST /job-targets/{id}/archive` |
| Match Assessments | `POST /match-assessments`, `GET /match-assessments`, `GET /match-assessments/{id}`, `POST /match-assessments/{id}/retry` |
| Scenarios | `GET /interview-scenarios`, `GET /interview-scenarios/{key}` |
| Interview Plans | `POST /interview-plans`, `GET /interview-plans/{id}`, `POST .../approve`, `.../reject`, `.../retry`, `.../regenerate` |
| Interview Sessions | `POST /interview-sessions`, `GET /interview-sessions`, `GET /interview-sessions/{id}`, and command endpoints for start/answer/pause/resume/skip/cancel/terminate/retry |
| Reports | `GET /interview-sessions/{id}/report`, `POST /interview-reports/{id}/recommendations/apply` |

Stable `data.error_code` values are namespaced strings such as `VERSION_NOT_READY`, `REVISION_CONFLICT`, `RESOURCE_EXPIRED`, `PRIVACY_REJECTED`, `DEPENDENCY_TIMEOUT`, and `STALE_RUN`. The top-level numeric code maps to the repository's shared error categories and is not used as the sole frontend recovery signal.

Mutation requests use `expected_revision` where resource state can race. Answer creation additionally requires an `Idempotency-Key` header. Reusing the same key and same payload returns the original command result; the same key with a different payload returns 409.

## 10. Interview Runtime Contract

The new workflow is one LangGraph inside the modular monolith:

```text
Session command
  -> deterministic Orchestrator selects stage/coverage
  -> Interviewer generates or reveals one question
  -> user answer interrupt
  -> local masking + PrivacyGuard
  -> Evaluator emits hidden structured evaluation
  -> deterministic coverage/follow-up decision
  -> next question, pause, or completion
  -> Celery Report task
```

"Retrieval" in the first release is a deterministic Source Catalog projection over the approved plan, JD evidence, resume evidence, prior questions, and answer evaluations. It does not activate `backend/rag/`, Qdrant, embeddings, reranking, web search, or a question bank.

Answer submission is durable and asynchronous:

1. Validate Session/revision/current question/idempotency and mask the answer.
2. Persist the accepted answer, set `turn_status=evaluating`, write `answer.submitted`, and commit.
3. Dispatch a bounded Celery turn task using the PID-owned async runner.
4. Worker evaluates outside a transaction.
5. Finalizer locks the Session, verifies run/revision/non-terminal ownership, persists evaluation/coverage/next question/events, and returns `turn_status=ready` or `retryable`.
6. Frontend polls the Session projection until the turn reaches a terminal turn state and never receives hidden evaluation fields.

Event payloads are per-type allow-lists. They may contain resource IDs, state names, stage/coverage keys, durations, attempts, safe error codes, and counts. They never contain question text, answer text, evidence text, prompts, completions, scores, feedback, credentials, or token replacement maps.

## 11. Frontend Information Architecture

Existing `/jobs` and `/jobs/:id` remain the JD library. New routes are:

| Route | Responsibility |
|---|---|
| `/targets/:id` | Minimal Job Target workspace and pinned/default inputs |
| `/targets/:id/matches/:assessmentId` | Version-pinned match report and actions |
| `/targets/:id/interview-plans/new` | Input/scenario/duration/difficulty/language selection |
| `/interview-plans/:id` | Public strategy/Coverage Matrix review and approval |
| `/interview-sessions` | Session history and filters |
| `/interview-sessions/:id` | Live text interview and recovery controls |
| `/interview-sessions/:id/report` | Completed/incomplete evidence-backed report |

Pages use typed modules under `frontend/src/api/` and `frontend/src/types/`. The current interview store is not expanded into a global cache; plan/session state remains page-local unless it must survive navigation. Polling stops on terminal state, timeout, page ownership loss, or visibility loss and refetches server state on resume.

Every route explicitly renders loading, empty, success, failure, mutation pending, and applicable conflict/expired states. Live interview layout keeps the current question, response editor, progress, and control bar dimensionally stable. Scores and feedback do not enter browser state until the report route loads.

## 12. Privacy And Security

- The platform remains an anonymous local single-user surface. No Spec in this program claims authentication, authorization, tenant isolation, or SaaS-grade object access control.
- JD/source content is untrusted input. Prompt instructions inside it cannot override system/schema constraints.
- Resume Version publication accepts masked snapshots only and runs PrivacyGuard before persistence and before every LLM call.
- Submitted answers run through local direct-identifier masking. Only masked answer text is persisted; no reversible answer manifest is stored.
- Private plan data, expected signals, rubrics, hidden evaluations, prompt content, raw provider output, and sensitive text are excluded from public DTOs, logs, events, screenshots, and test fixtures.
- URL import retains existing SSRF, redirect, MIME, size, and timeout enforcement. HTML and scripts are not persisted or executed.
- File/image tests use synthetic data. MinIO objects obey current JD retention and quarantine rules.

## 13. Compatibility And Migration

1. Each Spec creates one Alembic migration from the actual single head at implementation time; revision IDs are not predeclared in planning documents.
2. Existing ready JD rows are backfilled as version 1 using their current normalized content and available extraction metadata. Missing evidence remains explicitly unavailable.
3. `job_descriptions` stays the mutable compatibility projection. New downstream code accepts `jd_version_id`; old `jd_id`/copied `jd_text` paths remain legacy-only.
4. Resume Versions are created lazily from evaluated resumes or saved Builder revisions. Historical mutable resources are not bulk duplicated.
5. Existing `jd_match_results` remain readable. New assessments use `match_assessments`; there is no lossy conversion pretending legacy skill-only scores used `match-v1`.
6. Existing RIP-008 rows remain readable with nullable new version references. New plan creation writes the version-pinned contract.
7. Existing AIP-001 sessions are `contract_version=1` and remain on `/api/v1/interview`. New plan-driven Sessions are `contract_version=2` and use `/api/v1/interview-sessions`.
8. Legacy transcripts are not backfilled into events/evaluations because the missing history cannot be reconstructed reliably. Compatibility pages continue to read legacy rows.
9. Removing legacy columns, response fields, or routes requires separate usage evidence and a dedicated compatibility-removal issue.

## 14. Performance And Operations

- New history/list endpoints use keyset cursors over `(updated_at,id)` or `(created_at,id)`; existing JD page-number endpoints remain compatible.
- Foreign keys and common equality-plus-time filters use composite indexes with equality columns first.
- Partial indexes cover active Job Targets and queued/evaluating work instead of indexing all terminal rows.
- Session/report list projections JOIN or batch-load score/status summaries and do not load transcripts, private plans, or report bodies.
- LLM/OCR/report tasks use explicit SDK/gateway timeouts, Celery soft/hard limits, bounded transient retries, safe failure persistence, and run ownership.
- Session turn deadline is 180 seconds. Watchdog reconciliation marks overdue turns retryable; it never silently resubmits them.
- Metrics/log fields include resource ID, run ID, revision, task ID, operation, provider/model allow-list, duration, attempt, safe error code, and retryability only.

## 15. Delivery Order And Gates

```text
RIP-010 version/target foundation
  -> RIP-011 JD review/version publishing
  -> RIP-012 JD source expansion
  -> RIP-013 match assessment engine
  -> RIP-014 match report and RIP-008 bridge

AIP-013 scenario registry (may start after release gates)
  + RIP-013
  -> AIP-014 interview plan approval
  -> AIP-015 session state/events
  -> AIP-016 coverage runtime
  -> AIP-017 report/history/actions
```

Production implementation does not start until issue #038 and the Celery runtime correction are reviewed/shipped, worker and beat are restarted, RIP-007/RIP-008 browser acceptance is closed or explicitly waived, and the AIP-001 text path has a recorded browser baseline.
