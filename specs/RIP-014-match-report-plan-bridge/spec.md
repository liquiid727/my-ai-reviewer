# RIP-014 Match Report And Plan Bridge

> Derived from `spec-draft/resume-jd-match-assessment-2026-08-05.md`, RIP-008, and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | RIP-014 |
| Title | Match Report And Plan Bridge |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | RIP-008, RIP-013 |
| Prerequisites | completed Match Assessment query; Job Target workspace; RIP-008 revision/run contracts and browser acceptance |

## 2. Goal

Expose the completed Match Assessment as a complete evidence-backed report and update RIP-008 plan creation to retain exact Job Target/JD Version/Resume Version/Assessment references, while preserving all legacy plans and keeping every downstream action explicit.

## 3. Why This Exists

An engine result alone does not give users a coherent workflow. They need to understand versions, dimensions, caps, gaps, evidence quality, and actionable next steps from JD, resume, and target entry points. Existing RIP-008 plans use mutable `jd_id`/`resume_id` references, so directly linking the new report without a version bridge would reintroduce input drift.

This slice treats the report as a projection of one immutable assessment and extends the existing preparation-plan aggregate instead of creating a second task store.

## 4. Out of Scope

- Recomputing or editing Match Assessment results.
- Blocking Interview Plan creation based on score.
- Automatically editing a resume, Candidate Profile, Job Target status, or plan tasks.
- Interview Plan generation/runtime; AIP-014 and later Specs own those resources.
- Replacing RIP-008 scheduling, task CRUD, regeneration, or revision semantics.
- Converting legacy skill-only matches into `match-v1` reports.

## 5. Deliverables

- Report projection with version metadata, dimensions, cap explanation, gaps, evidence sufficiency, and actions.
- Unified create flow reachable from JD detail, resume detail, matching center, and Job Target workspace.
- Version-pinned RIP-008 plan creation and freshness rules with legacy compatibility.
- Target/report frontend routes, types, filters, loading/error/timeout/retry states, and explicit actions.
- End-to-end traceability and browser acceptance through assessment -> report -> preparation plan / interview-plan entry.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #112 | Version-pinned RIP-008 plan input bridge | Match US-008 | #057, #111 |
| #113 | Match report query and downstream action contracts | Match US-007/008 | #110, #112 |
| #114 | Match create/report/target frontend workflow | Match US-001/003/007/008 | #096, #113 |
| #115 | Target-to-report-to-plan end-to-end acceptance | All Match stories | #111, #114 |

## 6. Domain

### 6.1 Report Projection

The report is not a second mutable entity. It is a read projection over a completed Match Assessment plus immutable version summaries and current-target advisory metadata.

Sections are:

1. exact JD/Resume Version and policy/model metadata;
2. total score, pre-cap score, applied caps, confidence, and advisory recommendation;
3. eight dimensions with weights, evidence, and explanation;
4. four gap/risk categories with severity and action type;
5. evidence sufficiency and explicitly unknown conclusions;
6. stale advisory when target defaults/current JD Version have moved;
7. explicit actions for resume optimization, RIP-008 preparation plan, and Interview Plan creation.

Stale means a newer default/current version exists. It never changes the stored assessment, silently substitutes input, or hides the historical report.

### 6.2 RIP-008 Version Bridge

New job-search plans record `job_target_id`, `jd_version_id`, `resume_version_id`, and `match_assessment_id` in addition to existing root IDs. The application verifies that all references form one valid tuple and builds its Source Catalog from those immutable snapshots.

Existing plan rows with null version references remain readable/editable under the legacy contract. Regenerating a version-pinned plan uses its original version IDs unless the user explicitly creates a new plan. The plan title/progress/task/revision behavior remains RIP-008-owned.

### 6.3 Advisory Actions

No action executes on page load. Creating an Interview Plan remains allowed at every completed score. Creating a preparation plan uses the existing plan command; duplicate unfinished-plan recovery returns the existing plan. Resume optimization routes to the Builder/proposal flow with the selected Resume Version as context but does not mutate it.

## 7. Application

### 7.1 Queries

`MatchReportQueries.get(assessment_id)` batch-loads assessment, target, JD Version, Resume Version, and action eligibility without N+1. It never loads mutable full source rows when immutable summaries suffice.

`JobTargetQueries.get` adds recent assessment/plan/session summaries by bounded batch/JOIN projection, not one query per resource.

### 7.2 Plan Creation

The existing plan command accepts a new version-pinned variant. It validates the tuple, preserves current duplicate/revision/run behavior, and writes all references in its initial transaction. The LLM plan generator receives only immutable masked/source-catalog data and the selected Match Assessment.

### 7.3 Errors

| Error code | HTTP | Recovery |
|---|---:|---|
| `MATCH_ASSESSMENT_NOT_COMPLETE` | 409 | Continue polling/retry assessment |
| `PLAN_INPUT_SCOPE_MISMATCH` | 422 | Return to version selection |
| `PLAN_ALREADY_EXISTS` | 409 | Navigate to returned existing plan ID |
| `PLAN_REVISION_CONFLICT` | 409 | Reload before later mutations |
| `VERSION_STALE` | 200 advisory | Offer explicit new assessment; preserve current report |

## 8. Repository

Expected areas:

```text
backend/application/match_assessment/queries.py [MODIFY: report projection]
backend/application/plan_service.py             [MODIFY: version-pinned input]
backend/domain/job_search_plan/                 [MODIFY: source tuple validation]
backend/infrastructure/planners/                [MODIFY: immutable Source Catalog]
backend/api/v1/match_assessments.py             [MODIFY]
backend/api/v1/plans.py                         [MODIFY]
frontend/src/api/match-assessments.ts           [NEW]
frontend/src/types/match-assessments.ts         [NEW]
frontend/src/pages/MatchCreatePage.tsx          [NEW]
frontend/src/pages/MatchReportPage.tsx          [NEW]
frontend/src/pages/JobTargetPage.tsx            [MODIFY]
frontend/src/pages/PlanCreatePage.tsx           [MODIFY]
infra/alembic/versions/<revision>.py             [NEW]
```

Report display components accept public report DTOs only. They cannot receive the semantic adapter output or raw snapshots as props.

## 9. API

RIP-013 endpoints remain canonical. Completed `GET /api/v1/match-assessments/{id}` gains the full public report projection and an `actions` object with safe eligibility/route identifiers.

Job Target detail includes cursor-limited recent assessments and counts, with dedicated list endpoint for more results:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/job-targets/{id}/match-assessments` | Cursor report history |
| POST | `/api/v1/plans` | Existing legacy or new version-pinned create variant |

Version-pinned plan request:

```json
{
  "job_target_id": "uuid",
  "jd_version_id": "uuid",
  "resume_version_id": "uuid",
  "match_assessment_id": "uuid",
  "target_date": null,
  "weekly_hours": 6
}
```

The response never embeds complete JD/resume snapshots. Frontend navigation passes IDs and reloads server truth.

## 10. Database Impact

Add nullable, indexed `job_target_id`, `jd_version_id`, `resume_version_id`, and `match_assessment_id` FKs to `job_search_plans`, all `ON DELETE RESTRICT` for new history. Existing legacy columns remain non-breaking.

Add a partial uniqueness rule for version-pinned unfinished plans over the target/version tuple, consistent with RIP-008's unfinished statuses. Preserve the existing legacy uniqueness rule for rows whose new references are null. Equality fields precede status/time fields in supporting indexes.

Migration does not guess historical version references for old plans. It leaves them null and reports `input_contract=legacy` in queries. Downgrade removes only the new indexes/FKs/columns after later program tables are absent.

## 11. Test Plan

- Query: full report sections, explicit unknown evidence, cap explanation, stale advisory, immutable historical versions.
- Plan bridge: valid tuple, cross-target/version mismatch, duplicate unfinished plan, generation/retry/regeneration with original versions.
- Compatibility: legacy plans list/detail/edit/regenerate without fabricated version IDs.
- Performance: report/target/plan lists have bounded query count and cursor ordering stability.
- Frontend: all entry points converge on one create flow; queued/evaluating/failed/timeout/retry/completed states.
- Browser: low score still exposes Interview Plan action; stale report offers explicit rerun; plan creation navigates to existing/new plan correctly.
- Privacy: report and plan prompt contain only masked evidence and no provider/raw payload fields.

PRD mapping: Match US-001, US-003, US-007, US-008 and FR-23 through FR-28; all Match stories receive end-to-end coverage in #108.

## 12. Definition of Done

- [ ] Completed assessments render as evidence-backed reports without a second mutable report store.
- [ ] All entry points use one version-selection/create workflow and preserve exact IDs.
- [ ] Low score and risk labels remain advisory and never disable training.
- [ ] New RIP-008 plans retain the complete version tuple and reuse existing run/revision/task behavior.
- [ ] Legacy plans remain functional and clearly identify their legacy input contract.
- [ ] Query count, cursor, privacy, API, frontend, browser, migration, and compatibility checks pass.
