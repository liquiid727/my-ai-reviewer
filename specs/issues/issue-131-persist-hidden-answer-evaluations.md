# [AIP-016] Persist hidden Answer Evaluations

Separate v2 Answer Evaluation from the accepted masked answer and constrain evaluator evidence/output.

## Acceptance Criteria

- [ ] Create `answer_evaluations` with unique answer relationship, scores/signals/evidence/confidence/follow-up/coverage fields and indexes.
- [ ] Define strict evaluator schema and application-owned adapter using the existing LLM gateway.
- [ ] Accept only known question/coverage/source evidence IDs and reject numeric/schema disagreement.
- [ ] Keep external calls transaction-free with timeout and PrivacyGuard.
- [ ] Ensure v2 answers never write legacy score/feedback/raw-response columns.
- [ ] Migration/unit/gateway-spy tests cover normal, insufficient, malformed, malicious, timeout, and privacy rejection.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** #122, #130
- **SPEC:** AIP-016 sections 6.2/6.3, 8, 10
