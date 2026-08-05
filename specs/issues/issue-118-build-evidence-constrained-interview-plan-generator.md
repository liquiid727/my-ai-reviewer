# [AIP-014] Build evidence-constrained Interview Plan generator

Generate bounded public/private plan snapshots from exact inputs, Match evidence, and one scenario fixture.

## Acceptance Criteria

- [ ] Build a bounded Source Catalog from immutable JD/Resume Versions and the completed Assessment.
- [ ] Call the existing LLM gateway through a typed plan-generator adapter and PrivacyGuard.
- [ ] Validate scenario stages, duration question/follow-up budgets, coverage, evidence allow-list, difficulty, and language.
- [ ] Require high-importance/high-risk coverage or a safe duration-based omission reason.
- [ ] Reject unknown evidence, private/public field leakage, malformed output, and embedded prompt instructions.
- [ ] Fixture/fake/gateway-spy tests cover seven scenarios and all option sets without RAG.

- **Type:** backend
- **Priority:** high
- **Depends on:** #107, #117
- **SPEC:** AIP-014 sections 6.2 through 6.4, 7.1, 8
