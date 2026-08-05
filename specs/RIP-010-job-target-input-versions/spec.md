# RIP-010 Job Target And Input Version Foundation

> Derived from `spec-draft/resume-jd-match-assessment-2026-08-05.md`, `spec-draft/jd-import-library-2026-08-05.md`, and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | RIP-010 |
| Title | Job Target And Input Version Foundation |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | RIP-002, RIP-007, RIP-009 |
| Prerequisites | ready JD identities; evaluated masked resumes; saved Builder revisions; PrivacyGuard; single Alembic head |

## 2. Goal

Provide immutable JD Version and Resume Version resource foundations plus the minimal Job Target workspace that later matching, preparation-plan, and interview resources can reference without copying mutable input.

## 3. Why This Exists

Current matches and interviews reference mutable `jd_id`/`resume_id` resources or copied text. Editing a JD, reparsing a resume, or saving a Builder revision can therefore change what a historical result appears to mean. The new program also needs one idempotent grouping identity for downstream work, but creating it during JD import would incorrectly treat every saved role as an active target.

This slice establishes the shared identities and publication interface before any new scoring or interview behavior is implemented.

## 4. Out of Scope

- Rich JD extraction, review, publish commands, or version-history UI; RIP-011 owns those behaviors.
- Image/manual JD import; RIP-012 owns source expansion.
- Match scoring, Interview Plan generation, Session execution, or report generation.
- Job application stages, reminders, notifications, authentication, RBAC, or tenant isolation.
- Mutable editing of a published version or recovery of real PII from a Resume Version.
- Removing legacy mutable JD/resume fields or legacy interview routes.

## 5. Deliverables

- Domain contracts for `JDVersionRef`, `ResumeVersion`, `ResumeVersionSource`, and `JobTarget`.
- Alembic migration for `job_description_versions`, `resume_versions`, `job_targets`, and `job_descriptions.current_version_id`.
- Safe backfill of each existing ready JD as version 1 without inventing unavailable evidence.
- Application commands to publish-or-resolve a Resume Version and idempotently ensure/archive a Job Target.
- Queries for version selectors and Job Target detail/list projections.
- Version and target HTTP contracts plus frontend types and minimal target workspace/selector UI.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #092 | Input-version schema, migration and legacy JD v1 backfill | Match US-002; JD US-005 | #038 release gate |
| #093 | Job Target schema, domain invariants and migration | Match US-001 | #092 |
| #094 | Resume/JD Version publication and query API | Match US-002; JD US-005 | #092 |
| #095 | Job Target ensure/default/archive application and API | Match US-001 | #093, #094 |
| #096 | Target workspace and version-selector frontend | Match US-001/002; JD US-008 | #095 |

## 6. Domain

### 6.1 JD Version

A JD Version is an immutable published snapshot owned by one Job Description identity. It has a monotonically increasing `version_no`, content hash, schema version, normalized text, structured fields, evidence/provenance, source metadata, generator versions, publication reason, and publication timestamp.

This Spec defines the entity/table/query interface and backfill. RIP-011 owns review-to-publish behavior for new versions.

### 6.2 Resume Version

`source_type` is `parsed_resume` or `builder_draft`.

- Parsed-resume input requires an evaluated resume with an approved privacy manifest and stores a masked text/profile/evidence snapshot.
- Builder input requires an existing saved draft revision and stores the masked structured draft/profile/evidence snapshot for that exact revision.
- Publication computes a canonical content hash and runs PrivacyGuard before persistence.
- The same source revision/content hash resolves to the same version; changed source content creates a new version.
- No original file, real-value replacement map, filename-derived identity, raw direct identifier, or provider response is stored.

### 6.3 Job Target

A Job Target belongs to one Job Description identity and has `active` or `archived` lifecycle semantics. In the current anonymous single-user runtime, at most one non-archived target exists for a JD identity.

`ensure(jd_id, optional defaults)` is idempotent under concurrency. It returns the active row or creates it, and it may set current/default version references only when those versions belong to the selected JD/source. Changing a default increments `revision` and does not mutate historical resources. Archiving preserves all references and permits a later explicit downstream action to create a new active target.

## 7. Application

### 7.1 Module Interfaces

```text
ResumeVersionUseCases.publish_or_resolve(command) -> ResumeVersionResult
ResumeVersionQueries.list_for_source(query) -> CursorPage[ResumeVersionSummary]
JobTargetUseCases.ensure(command) -> JobTargetResult
JobTargetUseCases.update_defaults(command, expected_revision) -> JobTargetResult
JobTargetUseCases.archive(target_id, expected_revision) -> JobTargetResult
JobTargetQueries.get/list(...) -> projections
```

Callers provide source IDs and revisions, not arbitrary snapshots. The application loads source state, produces the canonical masked snapshot, runs PrivacyGuard, and persists through the version repository. Object construction remains at the application composition seam; API routes do not load ORM models or privacy adapters.

### 7.2 Concurrency And Transactions

- Resume publication performs source loading and PrivacyGuard outside the final write transaction, then locks/rechecks the source revision and inserts or returns the existing content key.
- Job Target ensure uses the partial unique index as the concurrency arbiter. A uniqueness race reloads the winning active target.
- Default-version updates lock the Job Target, validate version ownership, and update with `expected_revision` in one short transaction.
- JD backfill is deterministic and rerunnable by migration history; it never rewrites an existing version row.

### 7.3 Failure Semantics

| Error code | HTTP | Condition |
|---|---:|---|
| `SOURCE_NOT_READY` | 409 | Resume/profile/draft is not publishable |
| `SOURCE_REVISION_CHANGED` | 409 | Builder/source revision changed during publication |
| `PRIVACY_REJECTED` | 422 | Snapshot fails PrivacyGuard |
| `VERSION_NOT_FOUND` | 404 | Requested version does not exist |
| `VERSION_SCOPE_MISMATCH` | 422 | Default version does not belong to the selected identity |
| `REVISION_CONFLICT` | 409 | Job Target expected revision is stale |
| `JOB_TARGET_ARCHIVED` | 409 | Mutation targets an archived workspace |

Errors use safe messages and never echo snapshot content, privacy findings, or replacement values.

## 8. Repository

Expected implementation areas:

```text
backend/domain/versioning/                   [NEW: immutable version values/policies]
backend/domain/job_target/                   [NEW: target entity/policies]
backend/application/input_versions/          [NEW: publication/query use cases]
backend/application/job_target/              [NEW: commands/queries]
backend/api/v1/input_versions.py             [NEW]
backend/api/v1/job_targets.py                [NEW]
backend/infrastructure/db/models.py          [MODIFY or aggregate-owned split]
backend/infrastructure/db/repositories.py    [MODIFY: version/target adapters]
infra/alembic/versions/<revision>.py         [NEW]
frontend/src/api/job-targets.ts              [NEW]
frontend/src/types/job-targets.ts            [NEW]
frontend/src/pages/JobTargetPage.tsx         [NEW]
frontend/src/components/versions/            [NEW]
```

If AIP-011 has split ORM models before implementation, use the resulting aggregate files and metadata registration instead of adding new classes to the monolith file. Do not introduce compatibility re-exports without a removal issue.

List queries use keyset pagination over `(updated_at,id)`. Version selectors fetch summaries only and load the full masked snapshot only on an authorized detail query.

## 9. API

### 9.1 Endpoints

| Method | Path | Contract |
|---|---|---|
| POST | `/api/v1/resume-versions` | Publish/resolve exact parsed-resume or Builder revision |
| GET | `/api/v1/resume-versions` | Cursor list filtered by source reference |
| GET | `/api/v1/resume-versions/{version_id}` | Read immutable masked version detail |
| GET | `/api/v1/jd/{jd_id}/versions` | Cursor list of published JD versions |
| GET | `/api/v1/jd/{jd_id}/versions/{version_id}` | Read immutable JD version detail |
| POST | `/api/v1/job-targets` | Idempotently ensure active target for `jd_id` |
| GET | `/api/v1/job-targets` | Cursor list, optional active/archived filter |
| GET | `/api/v1/job-targets/{target_id}` | Target summary/default inputs/activity counts |
| PATCH | `/api/v1/job-targets/{target_id}` | Revision-checked default-version update |
| POST | `/api/v1/job-targets/{target_id}/archive` | Revision-checked archive |

### 9.2 Create Resume Version

```json
{
  "source_type": "builder_draft",
  "resume_id": null,
  "draft_id": "uuid",
  "source_revision": 12
}
```

Exactly one source reference is required. The response exposes ID, source summary, source revision, content hash, schema/privacy versions, and publication time. It returns masked content only on detail, not list.

### 9.3 Ensure Job Target

```json
{
  "jd_id": "uuid",
  "default_jd_version_id": "uuid-or-null",
  "default_resume_version_id": "uuid-or-null"
}
```

Repeated and concurrent requests return the same active target. Merely reading/importing/publishing a JD never calls this command.

## 10. Database Impact

### 10.1 `job_description_versions`

Required columns: UUID `id`, indexed FK `job_description_id ON DELETE RESTRICT`, positive `version_no`, `normalized_text`, `structured`, `evidence`, `source_metadata`, 64-character `content_hash`, `parser_version`, nullable `model_name`, `schema_version`, `publication_reason`, and `published_at timestamptz`.

Constraints:

- unique `(job_description_id, version_no)`;
- unique `(job_description_id, content_hash, schema_version)`;
- no application update/delete command;
- all downstream FKs use `ON DELETE RESTRICT`.

### 10.2 `resume_versions`

Required columns: UUID `id`; `source_type`; nullable indexed FKs to `resumes` and `resume_drafts`; `source_revision`; `content_hash`; `masked_snapshot`; `profile_snapshot`; `evidence_catalog`; parser/schema/privacy-policy versions; and `published_at`.

Checks require the source fields for exactly one source type. Partial unique indexes enforce one content snapshot per parsed resume and one per Builder revision/content hash.

### 10.3 `job_targets`

Required columns: UUID `id`; indexed FK `job_description_id`; nullable indexed default JD/Resume Version FKs; positive `revision`; `created_at`, `updated_at`, and nullable `archived_at`.

A partial unique index on `job_description_id WHERE archived_at IS NULL` enforces the current anonymous-scope invariant. A composite `(updated_at DESC,id DESC)` index supports target history. Future multi-user ownership requires a separate migration and cannot silently broaden this invariant.

### 10.4 Migration

The migration uses the actual Alembic head at implementation time. It creates version tables before adding `job_descriptions.current_version_id`. Existing ready JDs are inserted as version 1 and linked in the same migration; missing metadata is represented as `legacy`/`unavailable`, not fabricated. Downgrade removes only new references/tables after checking no later program migration depends on them.

## 11. Test Plan

- Domain: source-shape validation, immutability, target default ownership, archived behavior.
- Unit: canonical hashing, parsed/Builder snapshot construction, PrivacyGuard rejection, idempotent publication.
- Migration: clean upgrade, production-shape upgrade, ready-JD v1 backfill, rerun protection, downgrade from this head.
- Integration: concurrent target ensure, concurrent Resume Version publish, revision conflict, not-ready and scope-mismatch branches.
- Frontend: loading/empty/failure/conflict/archived states and version-selector persistence.
- Privacy: synthetic direct-identifier canaries never enter version rows, responses, logs, or fixtures.
- Performance: target/version list query count is constant and the expected indexes are used in representative plans.

PRD mapping: JD US-005/006/008 and FR-17/18/19/21/29; Match US-001/002 and FR-1 through FR-7, FR-28.

## 12. Definition of Done

- [ ] Version and Job Target interfaces are typed, documented, and callable only through application use cases.
- [ ] Existing ready JDs have one immutable v1 snapshot without invented evidence.
- [ ] Resume Versions contain masked snapshots only and fail closed through PrivacyGuard.
- [ ] Concurrent publication/ensure operations are idempotent and produce no duplicate active resources.
- [ ] Default-version mutations use revision control and cannot cross identity ownership.
- [ ] All new foreign keys, active filters, and cursor lists have verified indexes.
- [ ] API/frontend types and i18n cover all defined states and errors.
- [ ] Migration, unit, integration, privacy, frontend, and browser checks pass with synthetic data.
