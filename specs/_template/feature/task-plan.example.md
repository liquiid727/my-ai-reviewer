# Task Plan Example

## Meta

- Spec ID: `RP-002`
- Source Spec: `specs/RP-002-decision-api/spec.md`
- Status: `planned`

## Purpose

Translate the feature spec into explicit implementation, review, and verification work items.

## Task Model

Required fields:

- Task ID
- Owner agent
- Source spec, rule, or review gate
- Inputs
- Outputs
- Dependencies
- Acceptance evidence
- Current status

## Task Table

| Task ID | Owner Agent | Source | Inputs | Outputs | Depends On | Acceptance Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `RP-002.design-check` | `architecture-agent` | `spec.md` | `design/`, `specs/roadmap.md`, `spec.md` | design fit notes | design exists | approved design fit | pending |
| `RP-002.implementation` | `implementation-agent` | `spec.md` | `spec.md`, design fit notes | code changes, implementation notes | design check approved | deliverables complete | pending |
| `RP-002.review` | `reviewer` | `spec.md` | `spec.md`, implementation notes | review findings | implementation complete | review approved or waived | pending |
| `RP-002.verification` | `testing-agent` | `spec.md` | `spec.md`, API contract, test plan | tests/plans, tests/results | implementation complete | independent test pass | pending |

## Traceability Rules

- A task without a `spec_id` source is not actionable.
- A task without acceptance evidence does not satisfy definition of done.
- Implementation tasks must not consume private testing notes.
- Testing tasks must not consume private implementation notes.
