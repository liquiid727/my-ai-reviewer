# SPEC: RIP-009 Resume Privacy

> Source: approved privacy design, 2026-08-04
> Target branch: `main` | Base commit: `89c87f6`
> Status: Approved

## Summary

RIP-009 makes resume-derived data private by default. Uploaded files are held only in an encrypted quarantine while local redaction runs. Persisted text, facts, profiles, drafts, evidence, histories, and every resume-derived LLM request contain typed placeholders only. Real values and photos may be supplied for one preview/export request and are never persisted.

## Privacy Contract

- Sensitive types: person, phone, email, precise address, account/id, URL, organization, client, school, proprietary project/product, and photo.
- Placeholders use stable per-resource tokens such as `[[PERSON_01]]` and `[[ORG_01]]`.
- A privacy manifest stores token type, occurrence count, masked context, engine/policy versions, and review state. It never stores an original value.
- LLM work is allowed only for an approved manifest and a payload that passes residual scanning.
- Quarantined originals are application-encrypted, deleted immediately after approval, and expire after one hour when review is abandoned.
- Missing export replacements remain masked. Replacement values and uploaded export photos exist only in process/browser memory.

## State And Data Model

Resume processing becomes:

```text
uploaded -> privacy_scanning -> privacy_review_required -> text_masked
                              -> text_masked (automatic approval)
text_masked -> fact_extracted -> classified -> evaluated
any pre-approval failure/expiry -> failed + quarantine deletion
```

- Rename the persisted resume text contract from `raw_text` to `masked_text`.
- Add `resume_privacy_manifests` with one row per resume: status, revision, policy/engine versions, safe placeholders, risk flags, quarantine object/expiry, and review timestamps.
- Add a safe privacy manifest JSON object to each draft so new draft edits can allocate placeholders without retaining originals.
- Remove persistent resume photos and hydrated PDF exports. Existing object records are purged by remediation.

## Local Redaction

- `PrivacyRedactor` combines deterministic recognizers for contact/id/link/address/company suffix patterns, resume-layout recognizers, and local Chinese/English NER.
- Production images preload the NER models; runtime download is forbidden. If the configured engine is unavailable, processing fails closed.
- Overlapping findings prefer the widest high-confidence span. Repeated normalized values share one token.
- Redaction runs before database text persistence and before any LLM call. Model output is scanned again before persistence.
- Review-required previews are no-store responses. Manual masks use revision-checked character spans; approval reruns the complete scan.

## API Contract

- `POST /api/v1/resume/upload` returns `resume_id` and privacy-processing status; no durable `file_id` is exposed.
- `GET /api/v1/resume/{id}/privacy` returns only the masked candidate preview, safe manifest, revision, risks, and expiry.
- `POST /api/v1/resume/{id}/privacy/masks` accepts revision-checked `{start,end,entity_type}` spans.
- `POST /api/v1/resume/{id}/privacy/approve` performs the final scan, deletes quarantine, and starts the LLM pipeline.
- `GET /api/v1/resume/{id}` returns `masked_text` and a privacy summary instead of `raw_text`.
- `POST /api/v1/builder/{id}/preview` and `/export` accept multipart `payload` JSON plus an optional photo. The payload contains layout options and an exact token-to-value replacement map.
- Preview/export responses include `Cache-Control: no-store`; replacements for unknown tokens are rejected without echoing submitted values.

## Builder And LLM Rules

- Draft titles and local browser history cannot derive from the uploaded filename or real name.
- All draft writes are sanitized before persistence. Builder Assistant cannot write real identity fields and rejects sensitive instructions.
- Extraction, evaluation, Builder AI, interview generation, matching, and plan generation use the central privacy guard.
- Hydration substitutes exact tokens in a validated structured draft copy before Jinja autoescaped rendering.
- Export photos are decoded/processed in memory and never uploaded. Preview, download, and print use the same hydrated PDF blob.

## Legacy Remediation

- A dry-run inventories affected rows/objects without exposing values.
- Execute mode redacts recoverable resume/draft data, deletes originals, photos, persisted PDFs and unsafe AI histories, invalidates resume-derived plans/interviews, and queues fresh analysis from masked text.
- The command is idempotent and requires an explicit confirmation flag.

## Definition Of Done

- [ ] Maintained Chinese/English privacy fixtures have zero annotated cleartext in DB, logs, LLM payloads, masked APIs, and masked PDFs.
- [ ] Auto-approved, review-required, manual-mask, expiry, unavailable-engine, and cleanup paths pass.
- [ ] Every resume-derived LLM entry point is guarded and covered by a gateway-spy test.
- [ ] Builder stores only masked content; transient replacements/photos create no database or MinIO writes.
- [ ] Upload review and export preview cover empty, loading, success, and failure states on desktop and mobile.
- [ ] Legacy remediation dry-run and execute mode are tested for idempotency.

## Assumptions

- Anonymous single-user operation remains unchanged; authentication/RBAC is out of scope.
- The policy applies to resume-derived data. Independently entered target JD data is outside RIP-009.
- Local NER assets are mandatory deployment artifacts and privacy processing fails closed without them.

