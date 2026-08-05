# [AIP-016] Build the plan-driven v2 LangGraph

Add a v2 workflow that orchestrates one planned question/follow-up at a time through application interfaces.

## Acceptance Criteria

- [ ] Add separate v2 state/graph/nodes without changing the legacy AIP-001 graph.
- [ ] Keep deterministic Orchestrator separate from LLM Interviewer and evidence projection.
- [ ] Load exact approved plan/scenario/current coverage and persist no state directly from nodes.
- [ ] Generate/reveal one question with stage/coverage/parent links and bounded private evidence.
- [ ] Preserve relational state as authority and repair/rebuild checkpoint state safely.
- [ ] Graph/node tests cover question, follow-up, stage transition, pause, finish, and checkpoint mismatch.

- **Type:** backend
- **Priority:** high
- **Depends on:** #118, #124, #129
- **SPEC:** AIP-016 sections 6.1/6.2, 7.1, 8
