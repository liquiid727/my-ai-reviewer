# [AIP-013] Add versioned Interview Scenario registry

Add one validated code-backed registry and read API for all seven first-release scenarios.

## Acceptance Criteria

- [ ] Define exact scenario/stage/budget/follow-up/skip/scoring value objects and registry interface.
- [ ] Add seven version-1 fixtures with stage weights totaling 100.
- [ ] Enforce durations 15/30/45/60, question/follow-up budgets, depth 2, skip limits, candidate-question bounds, difficulty, and language.
- [ ] Fail deterministically on duplicate/invalid fixture data rather than falling back.
- [ ] Expose list/detail/version endpoints with public policy only and synchronized frontend types/i18n.
- [ ] Unit/API/type tests prove prompts/questions/signals/rubrics are absent.

- **Type:** backend
- **Priority:** high
- **Depends on:** issue #038 delivery gate
- **SPEC:** AIP-013 sections 6 through 12
