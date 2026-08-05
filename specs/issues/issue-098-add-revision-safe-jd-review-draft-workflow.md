# [RIP-011] Add revision-safe JD review-draft workflow

Make successful extraction enter an explicit review state and add revision-safe structured editing without changing source text.

## Acceptance Criteria

- [ ] Expand JD state/step constraints for `needs_review`, `review`, and safe draft metadata.
- [ ] Finalizers write a review draft only when run ownership remains current.
- [ ] Add `PATCH /jd/{id}/review` with `expected_review_revision` and explicit-clear semantics.
- [ ] Preserve field/item provenance and mark human changes `manual`.
- [ ] Expose current-version usability separately while a ready JD has a processing/review draft.
- [ ] Tests cover concurrent edits, stale runs, manual provenance, invalid evidence, and safe errors.

- **Type:** backend
- **Priority:** high
- **Depends on:** #097
- **SPEC:** RIP-011 sections 6.2/6.3, 7.1/7.2, 9.1
