# [AIP-010] Reconcile Builder and privacy failing-test contracts

Resolve the four behavior failures identified by the architecture review and lock the approved privacy/Builder behavior with focused tests.

## Acceptance Criteria
- [x] Photo rendering and Builder identity behavior match the approved RIP-009/RIP-004 contracts
- [x] The four reviewed failures pass without deleting tests or weakening assertions
- [x] Empty, failure, optional-imaging, and masked-identity branches are covered
- [x] Targeted suites and the complete backend pytest suite pass
- [x] **Review fix round:** `create_draft_from_profile` single-sanitize retains real `privacy_manifest`; `update_draft` never wipes non-empty placeholders; export hydration accepts tokens from manifest ∪ content

- **Type:** backend
- **Priority:** high
- **Depends on:** #070
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 3, 11)
- **Evidence:** `tests/results/20260804T074102Z-aip010-issue-073-builder-privacy-test-baseline.json`
- **Prior evidence:** `tests/results/20260804T073022Z-aip010-issue-073-builder-privacy-test-baseline.json`

## Implementation notes

- `update_draft` merges identity from existing + incoming, always strips client `photo`, and **preserves** confirmed `identity.photo` set via `set_draft_photo`.
- `_sanitize_draft_for_persistence` protects the `photo` key so MinIO object-name refs are not redacted.
- Export contract locked: `export_draft_pdf` does **not** auto-load `identity.photo` from MinIO; request-scoped `photo_data_uri` only (RIP-009).
- `profile_to_draft` returns **unsanitized** draft; create path runs a **single** sanitize and persists that manifest (P1 review fix).
- `update_draft` merges newly-redacted placeholders with existing `privacy_manifest` + content-present `[[TYPE_NN]]` tokens — never blanks a good manifest with `[]`.
- `export_draft_pdf` builds `allowed_tokens` from manifest ∪ tokens present in content (defense in depth).
- `set_draft_photo` rejects `data:` URI / embedded base64 / empty / >512-char values (P2 cheap guard).

## Residual (not in scope this round)

- Reviewer P2 hybrid UX: full API/FE rewiring of GET preview photo — deferred intentionally.
