# [AIP-016] Implement deterministic coverage and follow-up policies

Implement pure stage, coverage, time, follow-up, candidate-question, and skip decision rules.

## Acceptance Criteria

- [ ] Select eligible Coverage Items by exact deterministic importance/sufficiency/asked/risk/key ordering.
- [ ] Respect scenario stage order, question/follow-up/depth/time budgets, skip status, and planned counts.
- [ ] Advance stage or mark `not_reached` with safe reasons when coverage/time ends.
- [ ] Trigger follow-up only for vague/shallow/contradictory/missing evidence and stop on sufficient evidence/depth/budget.
- [ ] Support 1-3 candidate questions where the scenario allows and prohibit invented internal-company facts.
- [ ] Pure fixture tests cover ties, no time, all statuses, seven scenarios, and boundary budgets.

- **Type:** backend
- **Priority:** high
- **Depends on:** #116, #123
- **SPEC:** AIP-016 sections 6.1/6.2, 11
