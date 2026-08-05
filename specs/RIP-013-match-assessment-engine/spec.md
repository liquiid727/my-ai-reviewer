# RIP-013 Match Assessment Engine

> Derived from `spec-draft/resume-jd-match-assessment-2026-08-05.md` and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | RIP-013 |
| Title | Match Assessment Engine |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Backend Agent |
| Depends On | RIP-003, RIP-010, RIP-012 |
| Prerequisites | immutable ready JD/Resume Versions; active Job Target command; Candidate Profile evidence; LLM gateway and PrivacyGuard; corrected Celery runtime |

## 2. Goal

Create a reproducible asynchronous Match Assessment for one exact JD Version, one exact Resume Version, and one scoring-policy version, with deterministic rules, constrained semantic evidence classification, explainable dimensions, caps, and gap categories.

## 3. Why This Exists

RIP-003 provides a useful required-skill match but references mutable JD/resume identities and primarily compares normalized skill names. It cannot explain experience, projects, responsibilities, business context, hard constraints, or evidence sufficiency, and historical results drift when input records change.

This slice preserves RIP-003 as a legacy result and introduces a separate version-pinned assessment aggregate. It does not reinterpret legacy scores as if they used the new policy.

## 4. Out of Scope

- Blocking interview training based on score or recommendation.
- Qdrant, embeddings, hybrid search, reranking, web enrichment, or company knowledge.
- Editing Resume/JD Versions or automatically changing Candidate Profile.
- Match report page composition and RIP-008 plan handoff; RIP-014 owns those consumers.
- User-defined weights, policy administration UI, or online model training.
- Migrating legacy `jd_match_results` into the new scoring policy.

## 5. Deliverables

- Versioned `match-v1` policy fixture with eight dimensions, caps, thresholds, and skill aliases.
- Typed Source Catalog and deterministic evidence normalization.
- Pure scoring/gap engine and constrained LLM semantic-classification adapter.
- `match_assessments` persistence, state/run ownership, safe failures, reuse, retry, and force re-evaluate behavior.
- Celery assessment task and command/query API.
- Unit, integration, privacy, stale-worker, and scoring fixture evidence.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #107 | Scoring policy, Source Catalog and deterministic gap engine | Match US-004/005/006 | #106 |
| #108 | Constrained semantic matcher and evidence validation adapter | Match US-005/006 | #107 |
| #109 | Assessment schema, lifecycle and migration | Match US-003 | #092, #093, #107 |
| #110 | Assessment worker, reuse/retry and command/query API | Match US-003 | #108, #109 |
| #111 | Privacy, replay, scoring and failure acceptance | Match US-003 through US-006 | #110 |

## 6. Domain

### 6.1 Assessment Identity

A Match Assessment records `job_target_id`, `jd_version_id`, `resume_version_id`, `policy_version`, run ownership, model/prompt versions, status, timestamps, and completed result. Completed result fields are immutable.

A normal create command returns the latest completed assessment for the same version/policy tuple. `force=true` creates a new assessment row. Only one `queued`/`evaluating` row may exist for that tuple at a time.

### 6.2 Source Catalog

Before an LLM call, the application creates stable evidence items:

```text
jd:<version>:requirement:<key>
jd:<version>:responsibility:<key>
resume:<version>:fact:<key>
resume:<version>:project:<key>
resume:<version>:profile:<key>
```

Each item contains a type, normalized claim, masked source excerpt or structured value, provenance, and confidence. The LLM receives only catalog items relevant to the requested dimensions and may cite only their IDs. Unknown IDs, contradictory category assignments, or output outside Pydantic bounds invalidate the semantic result.

### 6.3 Scoring Policy `match-v1`

| Dimension key | Weight |
|---|---:|
| `required_skills` | 25 |
| `experience_depth` | 15 |
| `project_evidence` | 20 |
| `responsibility_alignment` | 15 |
| `technical_stack` | 10 |
| `industry_context` | 5 |
| `basic_conditions` | 5 |
| `preferred_qualifications` | 5 |

Each dimension returns raw score `[0,100]`, weighted points, confidence, cited JD/resume evidence IDs, deterministic rule results, and an explanation. Total is the sum of weighted points rounded to two decimals.

Missing any policy-marked core required skill caps total at 75. A severe years gap caps total at 70; severe means the candidate's maximum evidenced relevant years are less than 60% of an explicit minimum of at least three years. When evidence cannot establish years, the engine emits `evidence_gap` and does not apply the severe-years cap. The lowest applicable cap wins and every applied cap is persisted.

### 6.4 Gap Categories

- `capability_gap`: available evidence shows the requirement is not met.
- `expression_gap`: evidence exists in candidate facts but the Resume Version does not clearly express alignment.
- `evidence_gap`: available evidence cannot support a positive or negative conclusion.
- `hard_constraint_risk`: explicit education, location, certification, work authorization, language, or years condition is at risk.

One JD requirement has at most one primary category. When classification remains uncertain, `evidence_gap` wins. Each gap contains severity, requirement ID, candidate evidence IDs or an explicit missing-evidence marker, confidence, and action type.

### 6.5 Recommendation

Recommendation bands are advisory labels defined in the policy fixture and never used as authorization guards. Every completed assessment, including a low score or high-risk result, is eligible for Interview Plan creation.

## 7. Application

### 7.1 Create Flow

1. Load both immutable versions and verify `ready`/privacy eligibility.
2. Ensure or validate the active Job Target for the JD identity.
3. Resolve the policy fixture and reuse a completed result unless `force=true`.
4. Insert `queued` assessment with run ID and dispatch after commit.
5. Worker marks `evaluating`, builds Source Catalog, runs deterministic rules, then calls the constrained semantic classifier.
6. Finalizer locks the assessment, verifies run/status ownership, validates evidence references, computes weighted score/caps, and writes one immutable completed result.

No external call holds a database transaction. Broker failure and terminal dependency failure persist a safe retryable/non-retryable diagnostic.

### 7.2 Retry And Stale Work

Retry is allowed only for `failed`, creates a new run ID on the same incomplete assessment, clears safe failure fields, and requeues. Explicit re-evaluate after completion creates a new row. Any worker whose run ID is no longer current exits without a result write.

### 7.3 Error Semantics

| Error code | HTTP | Meaning |
|---|---:|---|
| `ASSESSMENT_INPUT_NOT_READY` | 409 | One immutable version is unavailable |
| `ASSESSMENT_SCOPE_MISMATCH` | 422 | Target/JD Version identity mismatch |
| `ASSESSMENT_ALREADY_RUNNING` | 409 | Active row exists; response includes its safe ID |
| `ASSESSMENT_EVIDENCE_INVALID` | 502 | LLM output cites unknown/invalid evidence |
| `ASSESSMENT_DEPENDENCY_TIMEOUT` | 504 | Bounded external call timed out |
| `ASSESSMENT_FAILED` | 502 | Safe terminal dependency/schema failure |
| `PRIVACY_REJECTED` | 422 | Resume-derived payload failed closed |

## 8. Repository

Expected implementation areas:

```text
backend/domain/match_assessment/              [NEW: policy, schemas, pure engine]
backend/application/match_assessment/         [NEW: commands, queries, source catalog]
backend/infrastructure/matchers/               [NEW: constrained semantic adapter]
backend/tasks/match_tasks.py                   [NEW]
backend/api/v1/match_assessments.py            [NEW]
backend/celery_app.py                          [MODIFY: register task]
backend/infrastructure/db/                     [MODIFY: model/repository]
infra/alembic/versions/<revision>.py            [NEW]
backend/tests/unit/test_match_assessment_*.py  [NEW]
backend/tests/integration/test_match_assessment_api.py [NEW]
```

The pure engine accepts a policy plus validated evidence/rule facts and returns a result. It does not know SQLAlchemy, Celery, LLM providers, or HTTP. The semantic adapter is behind an application-owned interface because production uses the LLM gateway and tests use a deterministic fake.

## 9. API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/match-assessments` | Create/reuse/force assessment |
| GET | `/api/v1/match-assessments` | Cursor list by target/version/status |
| GET | `/api/v1/match-assessments/{id}` | Status or completed result |
| POST | `/api/v1/match-assessments/{id}/retry` | Retry failed assessment |

Create request:

```json
{
  "job_target_id": null,
  "jd_version_id": "uuid",
  "resume_version_id": "uuid",
  "policy_version": "match-v1",
  "force": false
}
```

When `job_target_id` is null, the command ensures the active target from the JD identity. Creation returns `202` with assessment ID, target ID, status, run ID, and reuse flag. Completed detail returns dimensions, total before/after caps, caps, gaps, evidence summary, confidence, policy/model metadata, and version summaries. It does not return provider raw output or unmasked content.

## 10. Database Impact

Create `match_assessments` with:

- UUID primary key and indexed FKs to Job Target, JD Version, and Resume Version using `ON DELETE RESTRICT`;
- status check `queued/evaluating/completed/failed`;
- `policy_version`, `run_id`, `attempt`, safe error code/details, retryability;
- `dimension_scores`, `rule_results`, `gaps`, `evidence_summary`, `caps_applied`, and recommendation JSON/text fields;
- `score_before_caps` and `total_score` as `numeric(5,2)` with 0-100 checks;
- overall confidence numeric with 0-1 check;
- model/prompt/schema versions and timestamps.

Indexes:

- `(job_target_id,created_at DESC,id DESC)`;
- `(jd_version_id,resume_version_id,policy_version,created_at DESC)` for completed reuse;
- partial unique active tuple where status is `queued` or `evaluating`;
- partial watchdog index on `(status,updated_at)` for active rows.

JSONB remains unindexed because initial queries filter relational identity/status fields. All FKs are explicitly indexed. Downgrade removes only this aggregate when no later AIP/RIP table references it.

## 11. Test Plan

- Policy fixtures: weights sum to 100, stable key set, bands/caps/aliases validate at startup.
- Pure engine: exact weighted totals, rounding, core-skill cap, severe-years cap, lowest cap, missing-years no cap.
- Gap fixtures: capability/expression/evidence/hard-risk scenarios and non-conflicting primary category.
- Evidence: valid/unknown/duplicate/contradictory IDs and malicious JD/resume instructions.
- Privacy: gateway spy proves masked allow-listed payload only; canary identifiers absent from DB/log/response.
- Lifecycle: reuse completed, force new row, active duplicate, broker failure, retry, timeout, stale worker.
- Integration: target ensure, version mismatch, API status/result, migration constraints/indexes.
- Replay: same versions/policy/fake semantic result produce the same completed score and explanation.

PRD mapping: Match US-003 through US-006 and FR-7 through FR-22, FR-24 through FR-26, FR-28.

## 12. Definition of Done

- [ ] Every completed assessment is pinned to exact versions and `match-v1`.
- [ ] All eight dimensions, weights, cap rules, evidence references, and four gap categories are executable and tested.
- [ ] Deterministic hard rules and semantic LLM classification have separate interfaces and responsibilities.
- [ ] Unknown evidence or PrivacyGuard failure cannot persist a successful result.
- [ ] Reuse, force, retry, broker failure, timeout, and stale-worker behavior are durable and observable.
- [ ] Low scores never block Interview Plan eligibility.
- [ ] Migration, unit, integration, privacy, replay, lint, and type gates pass.
