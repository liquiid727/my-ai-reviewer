# RIP-011 Tasks

**Feature:** Evidence-bound JD Matching

**Status:** Proposed

**PRD:** `spec-draft/jd-intelligence-v2-2026-08-05.md`

**SPEC:** `specs/RIP-011-evidence-bound-jd-matching/spec.md`

**Depends on:** RIP-002, RIP-003, RIP-009, RIP-010 and issue #092

## Issue List

- [ ] [issue-098: Versioned matching domain and data contracts](../../tasks/issues/issue-098-rip011-matching-contracts.md)
- [ ] [issue-099: Deterministic hard-filter policy](../../tasks/issues/issue-099-rip011-hard-filter-policy.md)
- [ ] [issue-100: Evidence Catalog and LLM multidimensional matcher](../../tasks/issues/issue-100-rip011-evidence-llm-matcher.md)
- [ ] [issue-101: Async matching service and compatibility APIs](../../tasks/issues/issue-101-rip011-async-matching-api.md)
- [ ] [issue-102: Matching privacy, model-regression and acceptance closeout](../../tasks/issues/issue-102-rip011-matching-acceptance.md)

## Dependency Order

```text
092 + 097 -> 098 -> 099
093 + 098 + 099 -> 100 -> 101 -> 102
```
