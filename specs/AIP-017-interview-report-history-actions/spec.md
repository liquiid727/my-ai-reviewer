# AIP-017 Interview Report, History And Actions

> Derived from `spec-draft/interview-runtime-report-2026-08-05.md`, RIP-008, and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-017 |
| Title | Interview Report, History And Actions |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | AIP-016, RIP-008, RIP-014 |
| Prerequisites | completed/terminated v2 Session projections; hidden Answer Evaluations; Coverage Matrix; RIP-008 manual-task/revision command; corrected Celery runtime |

## 2. Goal

Generate immutable evidence-backed complete or incomplete interview reports, expose efficient Session/report history and recovery projections, and let users explicitly apply selected recommendations to an existing RIP-008 plan without duplicate tasks or silent plan mutation.

## 3. Why This Exists

Current AIP-001 report generation summarizes answer rows but does not anchor claims to Coverage Items or distinguish a complete run from early termination. It also cannot turn selected recommendations into revision-safe existing preparation tasks. Session history currently loads report summaries with per-row queries and does not expose the new recovery states.

This slice makes report content an immutable outcome of hidden evaluations and coverage, while keeping mutable application metadata in separate recommendation rows.

## 4. Out of Scope

- Showing feedback during the live Session.
- Automatically changing Candidate Profile, Resume Version, Job Target status, or RIP-008 task completion.
- Creating a new preparation-task store, learning graph, memory system, or notification schedule.
- Re-evaluating answers during report generation without evidence.
- Migrating legacy AIP-001 reports into v2 coverage/report semantics.
- Voice/video behavior analytics, RAG, external company research, or comparative population ranking.

## 5. Deliverables

- Deterministic report aggregation input and constrained report-writer output.
- Complete/incomplete report lifecycle with independent `report_status`, run ownership, retry, and safe failure.
- Extended immutable interview report and separate recommendation application records.
- Recommendation apply command using RIP-008 manual-task/revision interface with idempotent partial-result semantics.
- Bounded-query Session/report/timeline projections and cursor filters.
- Report/history frontend routes with evidence, coverage, accessibility, recovery, and action states.
- End-to-end compatibility, privacy, browser, and traceability closeout.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #135 | Report aggregation domain and persistence model | Runtime US-008 | #132, #134 |
| #136 | Complete/incomplete report worker, lifecycle and retry | Runtime US-008 | #135 |
| #137 | Idempotent recommendation application to RIP-008 | Runtime US-009 | #112, #136 |
| #138 | Session/report/history/timeline query API | Runtime US-008/010 | #123, #136, #137 |
| #139 | Report and history frontend | Runtime US-008/009/010 | #138 |
| #140 | Full program runtime/report compatibility acceptance | Runtime US-001 through US-010 | #137, #139 |

## 6. Domain

### 6.1 Report Eligibility And Completeness

- Normal coverage completion changes Session to `completing`, sets `report_status=generating`, and requests a complete report.
- A terminated Session requests an incomplete report only when at least one Answer Evaluation exists. Session status remains `terminated` throughout.
- Zero evaluated answers produce no report; history states `insufficient_answers` and offers a new Session action.
- Expired/cancelled Sessions do not automatically generate reports.
- A report is one immutable row per Session. Retry changes report run metadata before completion but never overwrites completed content.

### 6.2 Aggregation

The application builds a deterministic aggregate from persisted Questions, masked Answers, Answer Evaluations, Session Coverage, Scenario policy, and exact version/plan IDs.

Report dimensions are technical correctness, technical depth, project authenticity, problem analysis, solution tradeoffs, communication structure, and job fit. Scenario fixtures define dimension weights. Numeric results aggregate validated Answer Evaluations; the report LLM may summarize and organize evidence but cannot create new scores or cite unknown IDs.

The report contains:

- completion type and answered/planned/skip/not-reached counts;
- overall and dimension results with policy versions;
- JD coverage counts/status and evidence links;
- strengths, risks, and recommendations, each with known evidence IDs or `insufficient_evidence`;
- immutable exact input/plan/scenario metadata;
- no provider raw output, private rubric, or unmasked content.

### 6.3 Recommendation

Each recommendation has a stable key, category, title, action text, priority, evidence IDs, optional target JD requirement, and suggested RIP-008 task fields. Content is immutable with the report.

Application metadata records whether it was applied, target plan/task IDs, applied timestamp, and last safe failure. This metadata lives outside the immutable report body.

### 6.4 Apply Semantics

The user selects recommendations and a current Job Target RIP-008 plan, previews tasks, then submits `expected_plan_revision`.

Recommendations are processed in stable key order. Each item calls the existing RIP-008 manual-task command and records its mapping in the same transaction as that task/revision mutation. Already-applied items are idempotent successes. If a later item encounters a revision/dependency conflict, prior committed items remain applied, remaining items stay unapplied, and the response reports per-item `applied/already_applied/failed/not_attempted` plus the latest known revision. Repeating the request never duplicates successful tasks.

## 7. Application

### 7.1 Report Flow

1. Session outcome atomically sets `report_status=generating`, report run ID, and `report.requested` event.
2. Celery task loads relational aggregate in bounded queries and calls the report writer outside a transaction.
3. Output validation checks dimension keys, numeric consistency, evidence allow-list, coverage totals, and recommendation keys.
4. Finalizer locks Session, verifies report run/status and terminal/completing state, inserts immutable report/recommendations, sets `report_status=completed`, transitions only a normal `completing` Session to `completed`, and writes `report.generated`.
5. Failure sets safe report failure/retryability without changing terminated fact or losing evaluations.

### 7.2 Query Flow

List projections JOIN/batch Session, plan, target, and small report summary fields. They never load transcript, private plan, full report, or answer/evaluation bodies. Timeline uses event cursor ordering. Report detail batch-loads recommendation apply metadata.

### 7.3 Retry And Stale Work

Report retry is allowed for `report_status=failed`, allocates a new run ID, and does not re-evaluate answers. A stale task cannot overwrite a completed report, terminal status, newer run, or recommendation metadata.

### 7.4 Errors

| Error code | HTTP | Meaning |
|---|---:|---|
| `REPORT_NOT_READY` | 409 | Continue polling or retry failure |
| `REPORT_INSUFFICIENT_ANSWERS` | 409 | Terminated with zero evaluated answers |
| `REPORT_EVIDENCE_INVALID` | 502 | Writer cited unknown evidence |
| `REPORT_DEPENDENCY_TIMEOUT` | 504 | Safe retryable report failure |
| `RECOMMENDATION_PLAN_MISMATCH` | 422 | Plan is outside Job Target/version policy |
| `RECOMMENDATION_ALREADY_APPLIED` | 200 item | Idempotent existing mapping |
| `PLAN_REVISION_CONFLICT` | 207/409 | Partial or zero-success reconciliation required |

## 8. Repository

Expected areas:

```text
backend/domain/interview_report/                [NEW]
backend/application/interview_report/           [NEW]
backend/infrastructure/reporting/               [NEW/extend report agent adapter]
backend/tasks/interview_report_tasks.py         [NEW or replace v2 path only]
backend/api/v1/interview_reports.py             [NEW]
backend/api/v1/interview_sessions.py            [MODIFY: history/report summary]
backend/application/plan_task_service.py        [REUSE through typed command]
backend/infrastructure/db/                      [MODIFY]
infra/alembic/versions/<revision>.py             [NEW]
frontend/src/api/interview-reports.ts           [NEW]
frontend/src/types/interview-reports.ts         [NEW]
frontend/src/pages/InterviewSessionReportPage.tsx [NEW]
frontend/src/pages/InterviewSessionListPage.tsx [MODIFY]
frontend/src/components/interview-report/       [NEW]
```

The report application module owns aggregation and recommendation orchestration. It calls the RIP-008 application interface and never inserts `job_search_plan_tasks` directly.

## 9. API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/interview-sessions/{id}/report` | Report status or immutable detail |
| POST | `/api/v1/interview-sessions/{id}/report/retry` | Retry failed report run |
| GET | `/api/v1/interview-reports/{id}` | Immutable report detail by report ID |
| POST | `/api/v1/interview-reports/{id}/recommendations/preview` | Validate selection and preview RIP-008 tasks |
| POST | `/api/v1/interview-reports/{id}/recommendations/apply` | Apply selected recommendations |
| GET | `/api/v1/interview-sessions` | Cursor history with target/scenario/status filters |
| GET | `/api/v1/interview-sessions/{id}/timeline` | Safe timeline from events |

Apply request:

```json
{
  "recommendation_ids": ["uuid-1", "uuid-2"],
  "plan_id": "uuid",
  "expected_plan_revision": 9
}
```

All success returns 200. Mixed success returns 207 with item results and latest revision. Conflict before any success returns 409. The response contains IDs/statuses and safe messages only, not evidence/answer text.

## 10. Database Impact

Extend `interview_reports` with `report_kind` (`complete/incomplete`), completion/coverage summaries, evidence map, scenario/evaluation/report policy versions, immutable content hash, generation run/model metadata, and generated timestamp. Add checks for score ranges and report kind. Existing v1 report columns remain readable.

Create `interview_report_recommendations` with report FK `ON DELETE CASCADE`, stable recommendation key/content/evidence/target requirement, suggested task JSON, nullable indexed plan/task FKs, applied timestamp, and safe apply failure fields. Unique `(report_id,recommendation_key)` prevents duplicates.

Add report-status/run/failure columns/indexes to `interviews` only if AIP-015 did not already create them. Add report list/index support on `(created_at,id)` and Session history on equality filters followed by `updated_at,id`. Every new FK is indexed.

The migration marks existing reports as `legacy` through `contract_version=1` handling rather than inventing complete/incomplete coverage. It does not rewrite existing report text or scores.

## 11. Test Plan

- Aggregation: complete/incomplete, dimension weights, skipped/not-reached coverage, evidence linkage, insufficient evidence.
- Writer: unknown evidence/recommendation key, numeric disagreement, malformed output, timeout, privacy canaries.
- Lifecycle: normal completion, terminated with one answer, terminated with zero answers, failure/retry, stale report worker.
- Apply: preview/cancel, all success, already applied, mid-batch conflict partial result, zero-success conflict, retry without duplicate tasks.
- RIP-008 regression: manual-task revision/progress/order behavior remains canonical.
- Query/performance: bounded list/report/timeline query counts, stable cursor, no private/transcript loads.
- Frontend/browser: waiting/failed/retry/complete/incomplete, coverage/evidence accessibility, action selection, partial reconcile, history/deep-link/recovery states.
- Compatibility: legacy AIP-001 reports remain available on legacy routes and are not presented as v2 coverage reports.

PRD mapping: Runtime US-008, US-009, US-010 and FR-29 through FR-36; #128 closes traceability for all Runtime stories.

## 12. Definition of Done

- [ ] Complete and terminated-incomplete reports preserve Session status facts and exact input/policy references.
- [ ] Every score/claim/recommendation derives from persisted evaluations/coverage or states insufficient evidence.
- [ ] Completed report content is immutable; apply metadata is stored separately.
- [ ] Recommendation application uses RIP-008 commands, handles partial conflicts, and never duplicates successful tasks.
- [ ] History/report/timeline queries are cursor-based, bounded, and exclude private payloads.
- [ ] Legacy reports remain explicitly legacy and unaffected.
- [ ] Migration, unit, integration, privacy, worker, frontend, browser, performance, lint, and type gates pass.
