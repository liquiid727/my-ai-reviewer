# RIP-011 JD Review And Version Publishing

> Derived from `spec-draft/jd-import-library-2026-08-05.md` and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | RIP-011 |
| Title | JD Review And Version Publishing |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | RIP-007, RIP-010 |
| Prerequisites | existing text/file/URL import pipeline; JDExtractor; version tables and backfilled current version; current Celery ownership contract |

## 2. Goal

Convert the existing mutable JD extraction result into an evidence-backed review draft and require an explicit, idempotent publish command before downstream consumers can use a new immutable JD Version.

## 3. Why This Exists

RIP-007 currently writes extracted fields directly to a `ready` JD row, and re-extraction can replace those fields. That is sufficient for a library MVP but cannot support reproducible matching and interviews. Users also cannot review richer requirements, confidence, or provenance before the result becomes downstream input.

This slice upgrades the three existing source modes first, so later source expansion inherits the same publish contract instead of creating another temporary lifecycle.

## 4. Out of Scope

- PNG/JPEG OCR and structured manual JD creation; RIP-012 owns those sources.
- Match scoring, Job Target creation, Interview Plan generation, or plan/session UI.
- Saving HTML snapshots, crawling authenticated pages, or executing source scripts.
- Deleting a historical version or mutating an already published snapshot.
- Removing legacy JD fields/endpoints during the compatibility period.

## 5. Deliverables

- Rich `JDReviewDraft` schema with evidence, confidence, provenance, and generation metadata.
- Expanded structured JD extraction output and strict Pydantic validation.
- `needs_review` lifecycle for all new/reparsed text, file, and URL inputs.
- Revision-checked review edits, publish, reparse, retry, abandon-draft, archive, and version-history queries.
- Idempotent transaction that creates a JD Version and switches `current_version_id`.
- JD detail review/version-history UI with downstream actions pinned to a concrete version.
- Legacy ready-row compatibility and integration/browser acceptance evidence.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #097 | Rich JD schema, evidence catalog and extractor validation | JD US-003 | #094 |
| #098 | Review-draft state, revision-safe edit and status API | JD US-002/004 | #097 |
| #099 | Idempotent publish and immutable version-history API | JD US-005/006 | #092, #098 |
| #100 | Reparse, retry, abandon, archive and legacy compatibility | JD US-006/007 | #099 |
| #101 | JD review, publish and version-history frontend | JD US-004/005/006/008 | #098, #099, #100 |
| #102 | Migration, downstream-version and browser acceptance | JD US-002 through US-008 | #101 |

## 6. Domain

### 6.1 Review Draft Shape

The structured draft contains:

- title, company, department, location, employment type, seniority;
- compensation range/currency/period when explicitly present;
- minimum/preferred years, education, languages, certificates, location constraints;
- responsibilities, required skills, preferred skills, domain/industry context, interview clues, and notes.

Each list item and hard requirement has a stable draft item key, normalized value, optional source evidence span/text, confidence in `[0,1]`, and provenance `source`, `llm`, or `manual`. Scalar uncertainty is `null`; list uncertainty is `[]`. No evidence means `evidence_status=unavailable`, not a fabricated quote.

The draft stores parser, model, prompt, and schema versions plus overall confidence. Source content is untrusted and cannot change the extraction instruction or schema.

### 6.2 Review And Publish Rules

- Extraction success produces `needs_review`; it never auto-publishes a new version.
- Review edits require `expected_review_revision`, preserve explicit clears, and mark changed fields/items `manual`.
- Source text is read-only in the structured editor.
- Publish validates required title, all schema bounds, evidence references, and current review revision.
- Publish canonicalizes the snapshot and resolves the RIP-010 unique content key. Repeated commands return the same version.
- Publishing sets the version current and leaves the draft projection aligned with it.
- Reparse starts a new run/draft while the previous current version remains ready for downstream use.
- Reparse protects manual fields by default; `overwrite_manual=true` is an explicit command option.
- Archive hides the identity from active lists but preserves versions and references.

### 6.3 Lifecycle

`processing`, `duplicate_pending`, `needs_review`, `ready`, `failed`, and `archived` are the allowed root states. Processing steps are `queued`, `source_extract`, `duplicate_check`, `structure_parse`, `review`, and `done`.

If a ready JD is being reparsed, root state is `processing` but `current_version_id` remains usable. Public summaries expose both draft processing state and current published version state so consumers do not infer that the current version disappeared.

## 7. Application

### 7.1 Flow

```text
existing import command
  -> persist identity/run
  -> source extraction and duplicate detection
  -> rich structured extraction outside transaction
  -> finalizer verifies run and writes review draft
  -> user saves revision-checked corrections
  -> publish validates/canonicalizes
  -> insert immutable JD Version + update current_version_id atomically
```

The JD application module owns all orchestration. API routes call commands/queries only; Celery tasks load one command and call the same finalizer used by tests. The extractor is an infrastructure adapter behind the existing extraction seam.

### 7.2 Retry And Ownership

- Every import/reparse/retry receives a new run ID.
- Broker handoff failure persists `failed`, safe code, failure step, and retryability.
- Provider/parser timeouts use existing bounded retry policy; invalid structured output retries once inside the extraction adapter and then fails safely.
- A finalizer verifies run ID and allowed source state. A stale run records no business mutation.
- Reparse failure restores a queryable `ready-with-failed-draft` projection through current version metadata; it does not rewrite the current version.

### 7.3 Errors

| Error code | HTTP | Recovery |
|---|---:|---|
| `JD_REVIEW_REQUIRED` | 409 | Open review before downstream action |
| `JD_REVIEW_CONFLICT` | 409 | Reload and reapply local edits |
| `JD_PUBLISH_INVALID` | 422 | Correct identified safe field errors |
| `JD_VERSION_UNCHANGED` | 200 | Return existing version idempotently |
| `JD_REPARSE_UNAVAILABLE` | 409 | Keep current version; inspect source/retryability |
| `JD_REFERENCED` | 409 | Archive instead of hard delete |
| `STALE_RUN` | 409/internal no-op | Reload current resource |

## 8. Repository

Expected areas:

```text
backend/domain/jd/schemas.py                    [MODIFY: rich draft/evidence]
backend/domain/jd/enums.py                      [MODIFY: state/step]
backend/domain/jd/services.py                   [MODIFY: merge/canonicalize/publish policy]
backend/application/jd_service/                 [MODIFY: review/publish/version queries]
backend/infrastructure/extractors/jd_extractor.py [MODIFY]
backend/tasks/jd_tasks.py                       [MODIFY]
backend/api/v1/jd.py                            [MODIFY]
frontend/src/api/jd.ts                          [MODIFY]
frontend/src/types/jd.ts                        [MODIFY]
frontend/src/pages/JDDetailPage.tsx             [MODIFY]
frontend/src/components/jd/                     [MODIFY/NEW review/version views]
infra/alembic/versions/<revision>.py             [NEW]
```

The public serializer has separate draft and `current_version` summaries. Version detail uses the immutable RIP-010 repository; it never reconstructs history from current mutable columns.

## 9. API

### 9.1 Endpoints

| Method | Path | Purpose |
|---|---|---|
| PATCH | `/api/v1/jd/{jd_id}/review` | Save structured review fields with expected revision |
| POST | `/api/v1/jd/{jd_id}/publish` | Publish current review draft idempotently |
| POST | `/api/v1/jd/{jd_id}/reparse` | Create a new processing run/draft |
| POST | `/api/v1/jd/{jd_id}/draft/abandon` | Abandon failed/unpublished draft and retain current version |
| POST | `/api/v1/jd/{jd_id}/archive` | Archive identity without deleting versions |
| GET | `/api/v1/jd/{jd_id}/versions` | RIP-010 cursor version history |
| GET | `/api/v1/jd/{jd_id}/versions/{version_id}` | Read-only version detail |

Existing import/list/detail/retry/duplicate routes remain. Their response types gain `review_revision`, `draft_status`, `current_version`, `failure`, and safe processing metadata.

### 9.2 Publish Request

```json
{
  "expected_review_revision": 4,
  "publication_reason": "user_confirmed"
}
```

The response returns immutable version summary and updated JD projection. It never returns private provider output.

### 9.3 Downstream Contract

New UI actions are enabled only when `current_version` exists and pass `jd_version_id`. The legacy `POST /jd/match` and old interview creation remain compatible but are not used by new pages. A future removal requires separate evidence and issue approval.

## 10. Database Impact

- Expand `job_descriptions.status` and `processing_step` checks.
- Add non-null `review_revision` default 0, nullable `archived_at`, draft structured/evidence/confidence/generation metadata JSONB fields, safe failure code/details, and current-draft content hash.
- Preserve current content columns as a compatibility/review projection; do not duplicate their values into a second mutable table in this slice.
- RIP-010 owns `job_description_versions` and `current_version_id`; this slice writes them through the publish transaction.
- Add composite indexes for `(user_id,status,updated_at,id)` and active archive filtering where the current anonymous schema supports it.
- Index all new/self/source foreign keys. Avoid GIN indexes on JSONB until a measured query needs them.

The migration maps existing `ready` rows to `review_revision=0` and preserves their backfilled v1. It does not force old data back through an LLM. Constraint replacement uses explicit drop/add operations supported by PostgreSQL/Alembic; it does not use invalid `ADD CONSTRAINT IF NOT EXISTS` syntax.

## 11. Test Plan

- Extractor fixtures: complete, sparse, conflicting, long-list, malformed output, unknown evidence, and prompt-injection JD.
- Domain: manual-field protection, explicit clear, confidence/evidence validation, canonical hash, idempotent publish.
- Worker: parser/provider timeout, broker failure, retry, reparse failure with current version preserved, stale run.
- Integration: import -> needs_review -> edit -> publish -> history; concurrent edit/publish; archive/referenced delete.
- Migration: legacy ready v1 remains current and readable; new state constraints accept only valid values.
- Frontend/browser: comparison layout, low-confidence warnings, unsaved local edit on failure, conflict recovery, version switching, reparse failure, archive.
- Contract: all new downstream links use a concrete `jd_version_id`; old version content remains byte-equivalent after new publication.

PRD mapping: all JD stories except image/manual portions of US-001, plus FR-6 through FR-10 and FR-12 through FR-29.

## 12. Definition of Done

- [ ] Existing text/file/URL imports end in `needs_review` and require explicit publish for a new version.
- [ ] Rich structured fields, evidence, confidence, provenance, and generator versions are validated and persisted safely.
- [ ] Review edits and publish commands are revision-safe and idempotent.
- [ ] Reparse/retry/stale-worker behavior cannot alter a historical version or remove the current usable version.
- [ ] Archive/reference rules preserve all downstream history.
- [ ] New UI passes `jd_version_id`; no new caller copies mutable `raw_text` as canonical input.
- [ ] Migration, backend, frontend, privacy, browser, and compatibility tests pass.
