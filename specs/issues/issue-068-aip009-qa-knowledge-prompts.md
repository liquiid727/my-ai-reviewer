# [AIP-009] QA knowledge package and prompt registry

Configure the QA Agent with scoped architecture, test-gate, error/logging knowledge and reusable audit prompts.

## Acceptance Criteria
- [x] QA skill defines authority, modes, knowledge routing, workflow, and non-negotiable checks
- [x] Architecture, testing, and observability references explain review reasoning without overriding rules
- [x] Project, change, refactor, and error/logging prompts use placeholders and synthetic-data constraints
- [x] QA remains unable to modify implementation, tests, thresholds, Git, or delivery state by default

- **Type:** agent
- **Priority:** high
- **Depends on:** #067
- **SPEC:** `specs/AIP-009-quality-governance-foundation/spec.md` (Sections 6-8)
- **Status:** accepted (local-reviewed)
- **Evidence:** `.agents/qa-agent.skill.md`, `skills/qa-quality-governance/**`, indexes; fixed change-gate synthetic constraint; Reviewer + QA after fix 2026-08-04
