# RIP-012 JD Source Expansion

> Derived from `spec-draft/jd-import-library-2026-08-05.md` and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | RIP-012 |
| Title | JD Source Expansion |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Full-stack Agent |
| Depends On | RIP-001, RIP-011 |
| Prerequisites | issue #030 OCR parser shipped; versioned JD review/publish lifecycle; existing MinIO/parser registry/SafeWebFetcher |

## 2. Goal

Add PNG/JPEG image import and structured manual creation to the existing JD library so all five source modes enter the same review, version publication, duplicate, failure, archive, and downstream workflow.

## 3. Why This Exists

Job descriptions frequently arrive as screenshots or incomplete notes rather than clean files or public pages. Building separate OCR or manual-JD stores would duplicate the JD aggregate and bypass the evidence/version contract. This slice extends only the source adapters and UI mode selection after RIP-011 has made review/publish canonical.

## 4. Out of Scope

- A general OCR platform, provider SDK, or image understanding beyond text extraction.
- Login-required pages, browser automation, bulk crawl, source synchronization, or change monitoring.
- Match scoring, interview-plan generation, or Job Target creation during import.
- Image editing, multi-image stitching, PDF conversion, or retaining visual-layout semantics.
- Custom JD schemas outside the fields defined by RIP-011.

## 5. Deliverables

- `image` and `manual` JD source types and validation policies.
- Image upload command using existing MinIO and parser/OCR registry contracts.
- Manual structured creation command that enters `needs_review` without an LLM call.
- Five-mode import dialog and typed API contracts.
- Duplicate, retry, stale-run, safe-error, archive, and cleanup behavior for the new sources.
- Integration and browser acceptance for all five source modes.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #103 | Image source validation, storage, OCR and worker flow | JD US-001/002/007 | #030, #102 |
| #104 | Manual source domain, create API and provenance | JD US-001/002 | #102 |
| #105 | Five-mode JD import UI and state handling | JD US-001/002/008 | #103, #104 |
| #106 | Source-expansion integration, storage and browser acceptance | JD US-001/002/007/008 | #105 |

## 6. Domain

`JDSourceType` becomes `text`, `file`, `url`, `image`, or `manual`.

### 6.1 Image Source

- Accept `.png`, `.jpg`, and `.jpeg` with MIME `image/png` or `image/jpeg` and the existing 10 MiB limit.
- Validate extension, MIME, magic bytes, non-empty dimensions, and decode limits before storage.
- Store through the existing JD MinIO prefix and `FileModel(owner_type="job_description")` contract.
- The parser registry resolves the shipped RIP-001 OCR parser. JD code does not import OCR provider SDKs.
- OCR output is plain source text plus parser warnings/evidence positions when available; it then enters duplicate detection and RIP-011 structured extraction.

### 6.2 Manual Source

- `title` is required and limited to 200 characters.
- Optional company, location, department, employment type, responsibilities, required/preferred skills, constraints, and notes use RIP-011 bounds.
- Submitted values have provenance `manual`, confidence 1.0, and no fabricated source quote.
- Manual creation is synchronous to `needs_review`, with no worker/run unless the user later requests structure parsing.
- Manual save does not publish a version and does not create a Job Target.

### 6.3 Duplicate Semantics

Images use file hash first and normalized OCR text hash after extraction. Manual entries use canonical structured/text hash. A duplicate enters `duplicate_pending`; user confirmation preserves a separate JD identity and then continues to review. Duplicate cancellation removes the unreferenced identity and its source object.

## 7. Application

### 7.1 Commands

```text
JDImportUseCases.import_image(file, allow_duplicate) -> JDImportResult
JDImportUseCases.create_manual(command) -> JDImportResult
```

Image import persists identity/source metadata before dispatch. Broker failure changes the row to retryable `failed`. Worker download/OCR runs outside a transaction; the finalizer verifies run ownership before writing source text and advancing to RIP-011 extraction.

Manual creation validates/canonicalizes outside ORM construction and writes the identity plus review projection in one short transaction.

### 7.2 Retry And Cleanup

- Image retry creates a new run and reuses the retained safe object only while it exists.
- Missing/corrupt objects produce `JD_SOURCE_UNAVAILABLE`, not an endless retry loop.
- Stale runs cannot delete or replace objects owned by a newer run.
- Archive preserves source metadata and published versions; hard delete follows RIP-011 reference checks.
- No raw OCR/provider exception is persisted or returned.

## 8. Repository

Expected areas:

```text
backend/domain/jd/enums.py                     [MODIFY]
backend/domain/jd/schemas.py                   [MODIFY: manual request]
backend/application/jd_import_service.py       [MODIFY]
backend/infrastructure/parsers/                [REUSE shipped OCR parser]
backend/infrastructure/storage/minio_client.py [REUSE bounded object access]
backend/tasks/jd_tasks.py                      [MODIFY: image source stage]
backend/api/v1/jd.py                           [MODIFY: image/manual endpoints]
frontend/src/api/jd.ts                         [MODIFY]
frontend/src/types/jd.ts                       [MODIFY]
frontend/src/components/jd/JDImportDialog.tsx [MODIFY]
infra/alembic/versions/<revision>.py            [NEW]
```

The import dialog remains one module with a small `source mode -> validated payload` interface. Mode-specific fields stay internal instead of creating five duplicate dialogs or five page-level fetch paths.

## 9. API

| Method | Path | Content type | Result |
|---|---|---|---|
| POST | `/api/v1/jd/import/image` | multipart | processing JD identity/run |
| POST | `/api/v1/jd/import/manual` | JSON | `needs_review` JD identity |

Image multipart accepts `file` and `allow_duplicate`. It does not accept arbitrary OCR configuration.

Manual request example:

```json
{
  "title": "Senior Backend Engineer",
  "company": "Example Co",
  "responsibilities": ["Own service reliability"],
  "required_skills": [{"name": "Go", "critical": true}],
  "notes": null
}
```

Errors include `JD_IMAGE_TYPE_UNSUPPORTED` (422), `JD_IMAGE_TOO_LARGE` (413), `JD_OCR_UNAVAILABLE` (503), `JD_SOURCE_UNAVAILABLE` (409), and existing duplicate/run/dependency failures. Error data never echoes file bytes, OCR text, or provider output.

## 10. Database Impact

- Replace the JD source-type check with all five values.
- Extend source/processing checks only where RIP-011 does not already include image flow states.
- No new table is required.
- Existing source-file FK/index and content-hash indexes are reused.
- Manual rows have no `source_file_id`/`source_url`; image rows require `source_file_id` after successful object persistence.

Migration upgrade and downgrade preserve all existing source values. Downgrade is blocked by normal Alembic ordering until image/manual rows have been handled by the operator; it must not silently coerce them to `file` or `text`.

## 11. Test Plan

- Unit: extension/MIME/magic-byte mismatch, size/decode bounds, manual bounds/provenance, source-type policy.
- Parser integration: synthetic PNG/JPEG OCR success, warnings, no-text, unavailable parser, timeout, corrupt image.
- Worker: broker failure, object missing, retry, duplicate by file/text hash, stale run, cleanup ownership.
- API: multipart validation and manual success/validation/duplicate branches using the shared envelope.
- Frontend: five mutually exclusive modes, invalid-submit disabled, switching does not leak another mode's payload, pending/failed/retry states.
- Browser: desktop/mobile import through review and publish for each mode; no text/control overlap or sensitive fixture data.
- Storage: expected MinIO write/delete behavior and no duplicate OCR implementation/import.

PRD mapping: JD US-001/002/007/008 and FR-1 through FR-11, FR-22 through FR-29 as applicable to source expansion.

## 12. Definition of Done

- [ ] All five source modes enter the same RIP-011 review/publish lifecycle.
- [ ] Image import uses the shipped OCR parser through the existing registry and creates no provider-specific JD code.
- [ ] Manual creation is evidence-honest, revision-ready, and does not invoke an LLM.
- [ ] Duplicate/retry/stale-run/object cleanup behavior is deterministic and tested.
- [ ] Import never creates a Job Target or publishes without user confirmation.
- [ ] API/types/i18n and desktop/mobile UI cover every required state.
- [ ] Migration, storage, backend, frontend, privacy, and browser checks pass.
