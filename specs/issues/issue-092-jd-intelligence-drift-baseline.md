# [JD Intelligence v2] PRD/SPEC/as-built drift baseline

## Description

Establish the factual baseline before feature implementation. Reconcile RIP-003, RIP-007 and RIP-008 against code and available tests, then publish a traceability matrix for the new PRD and RIP-010~012. Code presence must be reported separately from verified acceptance.

## Acceptance Criteria

- [ ] Correct RIP-003 statements that claim JD extraction, matching persistence or JD UI do not exist
- [ ] Record `rules_v1` exactly: inputs, 70/30 skill weighting, thresholds, fields not considered and absence of LLM/vector matching
- [ ] Audit RIP-007 issue #039~#047 and RIP-008 issue #048~#057 against code, migrations and tests; mark each as implemented, verified, partial or missing with evidence
- [ ] Do not mark a feature shipped solely because source files exist
- [ ] Add a PRD FR -> SPEC -> issue -> planned test traceability matrix for RIP-010~012
- [ ] Record unresolved conflicts in the relevant tasks/current blocker or handoff document
- [ ] Preserve the existing dirty worktree and avoid application-code changes
- [ ] `git diff --check` passes for documentation changes

## Dependencies

None

## Type

docs / governance

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - Current Baseline, US-010, FR-30

## SPEC Reference

`specs/RIP-010-jd-vision-import/spec.md`, `specs/RIP-011-evidence-bound-jd-matching/spec.md`, `specs/RIP-012-jd-matching-consumption/spec.md` - Meta and Definition of Done
