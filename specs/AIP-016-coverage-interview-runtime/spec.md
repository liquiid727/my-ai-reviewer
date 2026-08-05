# AIP-016 Coverage-Driven Interview Runtime

> Derived from `spec-draft/interview-runtime-report-2026-08-05.md`, AIP-001, and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-016 |
| Title | Coverage-Driven Interview Runtime |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | AIP-013, AIP-015, RIP-009 |
| Prerequisites | approved private Interview Plan; v2 Session/event/coverage schema; existing LLM gateway and AIP-001 interviewer/evaluator/follow-up capabilities; corrected Celery runtime |

## 2. Goal

Execute a text-only Interview Session according to scenario stages and Coverage Matrix, persist masked answers and separate hidden evaluations, generate bounded follow-ups, recover each turn safely, and expose no score or feedback before the report.

## 3. Why This Exists

Current AIP-001 generates a fixed question list, stores evaluation fields on answer rows, and returns score/feedback after every answer. It does not prioritize unverified high-risk requirements, separate evaluator state, make answer submission idempotent, or survive a worker/request interruption through durable turn ownership.

This slice builds a new v2 workflow beside the legacy graph. Deterministic orchestration owns coverage and budgets; LLM-facing modules generate one question, evaluate one masked answer, or generate one bounded follow-up.

## 4. Out of Scope

- Displaying score, feedback, expected answers, signals, or rubrics during a live Session.
- Final report generation, recommendation application, or report/history pages; AIP-017 owns them.
- RAG/Qdrant/question-bank retrieval, web/company research, long-term memory, or profile mutation.
- Voice/video/ASR/TTS, code execution, IDE, Sandbox, or whiteboard input.
- Changing the legacy `/api/v1/interview/{id}/answer` response.

## 5. Deliverables

- Pure coverage selector, stage/time budget policy, and follow-up/skip decision rules.
- Plan-driven v2 LangGraph state/graph/nodes with PostgreSQL business state as authority.
- Interviewer and Evaluator structured contracts with evidence allow-lists and PrivacyGuard.
- Durable asynchronous answer turn using idempotency key, revision, run ownership, timeout, retry, and stale-worker protection.
- Separate `answer_evaluations` persistence and v2 question/answer/event updates.
- Live Session frontend with stable question/editor/control layout and hidden evaluation contract.
- Runtime, concurrency, privacy, worker-restart, and browser acceptance evidence.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #129 | Coverage selector, time/follow-up/skip policies | Runtime US-002/004/006 | #116, #123 |
| #130 | Plan-driven v2 LangGraph and question generation | Runtime US-002/004 | #118, #124, #129 |
| #131 | Evaluator contract and separate Answer Evaluation persistence | Runtime US-003/007 | #122, #130 |
| #132 | Durable idempotent answer-turn worker and API | Runtime US-003/005/006 | #125, #131 |
| #133 | Live interview frontend with hidden feedback and controls | Runtime US-001 through US-006 | #127, #132 |
| #134 | Runtime recovery, privacy, worker and browser acceptance | Runtime US-001 through US-007 | #128, #133 |

## 6. Domain

### 6.1 Coverage Selection

At a main-question boundary, eligible Coverage Items must belong to the current scenario stage, not exceed planned counts, and not be terminally skipped/not-reached. The deterministic priority tuple is:

```text
importance descending
evidence sufficiency ascending
questions asked ascending
source risk priority descending
coverage key ascending
```

The selector first honors the ordered scenario stage. It advances when the stage budget is exhausted, all required coverage is sufficiently evaluated, or remaining active time cannot fit another main question. It never lets an LLM choose an arbitrary stage or exceed question/time budgets.

High-importance unverified items outrank lower-importance items. When time runs out, remaining items become `not_reached` with a safe reason for the report.

### 6.2 Question And Follow-Up

Main questions use approved private plan material and may be adapted to prior public context without introducing new evidence. Each persisted question references stage and one or more Coverage Items.

Evaluator output contains internal score, dimension scores, observed signals, missing signals, evidence references, confidence, coverage update proposal, `needs_followup`, and follow-up reason. It is stored separately and hidden from live DTOs.

A follow-up is allowed only when the scenario/turn budgets permit and the evaluation indicates vague, shallow, contradictory, or missing evidence. It references its parent question and coverage keys. Maximum depth is 2; sufficient evidence, depth limit, stage/time exhaustion, or total follow-up budget forces the next main question/stage.

Candidate-question stage accepts 1-3 candidate questions as defined by the scenario. The Interviewer must state when company-internal facts are unavailable and must not invent them.

### 6.3 Answer Contract

- Answer text length is 1-20,000 characters before masking.
- Local redaction replaces direct identifiers with typed placeholders; only masked text is persisted.
- PrivacyGuard runs before any LLM call and fails closed.
- Each answer command includes Session revision, current question ID, and `Idempotency-Key` header.
- Same key/same canonical payload returns the existing command result. Same key/different payload is a conflict.
- Accepted answer sets `turn_status=evaluating`; live response exposes no evaluation fields.

### 6.4 Turn Outcome

The worker may produce next question, follow-up, stage completion, normal Session completion, paused-after-evaluation, or retryable turn failure. It cannot reopen terminal Session states or overwrite a newer revision/run.

## 7. Application

### 7.1 Workflow Roles

```text
Orchestrator: pure deterministic stage/coverage/budget decision
Interviewer: constrained one-question/follow-up generation
Evaluator: hidden structured answer assessment
Evidence projection: deterministic Source Catalog selection, not RAG
```

These roles are nodes/modules inside one LangGraph workflow and process. They are not network services or autonomous multi-agent peers.

### 7.2 Durable Answer Flow

1. Command locks Session, validates state/revision/current question/idempotency, masks answer, inserts accepted answer, allocates run ID, writes `answer.submitted`, increments revision, and commits.
2. Dispatch `evaluate_interview_turn` after commit. Broker failure makes the turn retryable with a safe event.
3. Worker loads immutable private plan, question, masked answer, coverage projection, and scenario fixture.
4. Evaluator/Interviewer calls run outside transactions with gateway and task limits.
5. Finalizer locks Session, verifies run/revision/non-terminal ownership, persists Answer Evaluation, applies deterministic coverage decision, persists next question if any, writes ordered events, and clears or updates turn status.
6. If `pause_requested`, result persists but Session remains paused. If normal coverage ends, Session moves to `completing` and AIP-017 report dispatch begins when available.

### 7.3 Retry

Turn retries are user-triggered from `retryable`, use the same accepted answer and a new run ID, and never insert a duplicate answer. Transient provider retries are bounded to two attempts within the 180-second turn deadline. Watchdog marks overdue active turns retryable; it does not silently requeue.

### 7.4 Error Semantics

| Error code | HTTP | Recovery |
|---|---:|---|
| `ANSWER_QUESTION_MISMATCH` | 409 | Reload current Session |
| `ANSWER_IDEMPOTENCY_CONFLICT` | 409 | Use original payload/result or new key |
| `ANSWER_PRIVACY_REJECTED` | 422 | Remove unsafe direct identifiers/retry |
| `TURN_ALREADY_RUNNING` | 409 | Poll current turn |
| `TURN_RETRYABLE` | 409 | Explicit retry command |
| `TURN_DEPENDENCY_TIMEOUT` | 504 | Persist retryable turn |
| `TURN_EVIDENCE_INVALID` | 502 | Safe failure; no invalid evaluation persisted |
| `SESSION_EXPIRED` | 410 | Create a new Session from a plan |

## 8. Repository

Expected areas:

```text
backend/domain/interview_runtime/              [NEW: coverage/turn policies]
backend/application/interview_session/         [MODIFY: answer/turn use cases]
backend/workflow/graphs/plan_interview_graph.py [NEW]
backend/workflow/state_v2.py                   [NEW]
backend/workflow/nodes_v2/                     [NEW]
backend/agents/question_agent/                 [MODIFY/NEW v2 adapter]
backend/agents/evaluation_agent/               [MODIFY/NEW v2 adapter]
backend/agents/followup_agent/                 [MODIFY/NEW v2 adapter]
backend/tasks/interview_turn_tasks.py          [NEW]
backend/api/v1/interview_sessions.py           [MODIFY]
backend/infrastructure/db/                     [MODIFY]
frontend/src/api/interview-sessions.ts         [MODIFY]
frontend/src/types/interview-sessions.ts       [MODIFY: public types only]
frontend/src/pages/InterviewSessionPage.tsx    [MODIFY]
infra/alembic/versions/<revision>.py            [NEW]
```

The v1 graph/state/nodes remain unchanged. V2 graph nodes do not own SQLAlchemy sessions or call repositories directly; application use cases provide/load validated state and persist command outcomes.

## 9. API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/interview-sessions/{id}/answers` | Accept masked async answer turn |
| POST | `/api/v1/interview-sessions/{id}/turn/retry` | Retry persisted answer evaluation |
| GET | `/api/v1/interview-sessions/{id}` | Poll public turn/session projection |

Answer request:

```json
{
  "question_id": "uuid",
  "answer_text": "candidate input",
  "expected_revision": 7
}
```

The `Idempotency-Key` header is required and limited to a safe 128-character token. Accepted response is 202 with answer ID, revision, `turn_status=evaluating`, safe progress, and polling hint. Subsequent Session detail may include the next/current public question but never evaluation score, feedback, expected signals, rubric, or private evidence.

## 10. Database Impact

Create `answer_evaluations` with UUID primary key; unique indexed FK `answer_id ON DELETE CASCADE`; indexed question/session references; dimension scores, signals, evidence IDs, confidence, follow-up decision/reason, coverage proposal, model/prompt/schema versions, and created timestamp. Score/confidence checks enforce valid ranges.

Complete AIP-015 extensions on v2 questions/answers:

- unique answer `(question_id,idempotency_key)` and canonical payload hash;
- question parent/self FK, coverage keys, kind/status, generation key, public text, asked/skipped timestamps;
- answer `masked_text`, status, accepted timestamp, turn run ID, safe failure fields;
- v2 code never writes legacy `score`, `feedback`, `key_points_*`, `followup_question`, or `raw_llm_response` columns.

Add indexes for active turn watchdog, parent questions, Session question order, answer question/run, and evaluation Session/report aggregation. JSONB evidence arrays are not indexed in v1 because aggregation scopes by indexed Session/answer IDs.

## 11. Test Plan

- Pure coverage selector across importance, sufficiency, stage, time, skip, deterministic tie breaks, and no-time-left.
- Follow-up rules for vague/missing/contradictory/sufficient evidence, per-question depth, total budget, and stage completion.
- Answer validation/masking/idempotency/revision/concurrent-tab behavior.
- Gateway spies for hidden structured evaluation, unknown evidence, malformed output, timeout, and PrivacyGuard failure.
- Worker lifecycle: broker failure, transient retry, watchdog expiry, explicit retry, stale run, pause requested, terminate during work.
- Relational/checkpoint recovery after API/worker restart with the same current question and no duplicate evaluation.
- API/frontend assertions that live state never contains score/feedback/rubric/private-plan canaries.
- Browser desktop/mobile flow through start, answer pending, next/follow-up, pause/resume, skip, conflict, retryable failure, and completion.

PRD mapping: Runtime US-002, US-003, US-004, plus runtime portions of US-001/005/006/007; FR-6 through FR-20 and FR-23 through FR-28, FR-36.

## 12. Definition of Done

- [ ] Coverage/stage/time/follow-up decisions are deterministic and scenario-bounded.
- [ ] Every accepted answer is masked, idempotent, revision-safe, durable, and evaluated at most once per run outcome.
- [ ] Evaluations are separate from answers and absent from every live public/browser contract.
- [ ] V2 workflow nodes use application interfaces and do not persist directly.
- [ ] Retry, timeout, pause, terminate, expiry, checkpoint mismatch, and stale-worker paths converge safely.
- [ ] No RAG/Qdrant/voice/Sandbox runtime is activated.
- [ ] Migration, unit, integration, privacy, worker, frontend, browser, lint, and type gates pass.
