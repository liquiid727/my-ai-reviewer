# AIP-009 Quality Governance Foundation

> Derived from `spec-draft/engineering-quality-governance-2026-08-04.md` and `reviews/project-architecture-quality-2026-08-04.md`
> Generated: 2026-08-04 | Target branch: `main` | Base commit: `89c87f6`

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-009 |
| Title | Quality Governance Foundation |
| Epic | Engineering Quality Governance |
| Status | Proposed |
| Owner Agent | QA Agent |
| Depends On | none |
| Prerequisites | GoalSpec workflow, 2026-08-04 architecture review, existing QA Agent role |

## 2. Goal

Establish one enforceable quality-governance source of truth and give the QA Agent scoped knowledge, prompts, and evidence contracts for architecture, test gates, errors, logging, privacy, and release decisions.

## 3. Why This Exists

The review found good architecture intent but inconsistent implementation, stale Agent guidance, non-reproducible gate expectations, and no normalized project-quality evidence. Without a governance foundation, later CI and refactoring work can create competing rules or report planned checks as passed.

## 4. Out of Scope

- Fixing current Ruff, mypy, pytest, or frontend coverage gaps.
- Adding Make targets, GitHub Actions, or branch protection.
- Refactoring production modules or changing API behavior.
- Authorizing QA to modify implementation, thresholds, tests, or delivery state.

## 5. Deliverables

- Stable quality architecture covering ownership, dependency direction, directory shape, patterns, gates, error/logging contracts, and rollout.
- Normative architecture-boundary and quality-gate rule sets.
- Project QA skill with task-specific knowledge routing and reusable prompts.
- QA evidence template with explicit `PASS/FAIL/BLOCKED/NOT_RUN` semantics.
- Cross-links from design/rules/skills/Agent indexes and a local issue plan.

## 6. Domain

Quality status is a closed vocabulary:

- execution: `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`;
- decision: `GREEN`, `YELLOW`, `RED`, `BLOCKED`;
- severity: `P0`, `P1`, `P2`, `P3`.

A `QualityFinding` has a stable finding ID, rule/requirement ID, severity, location, observed evidence, baseline classification, recommendation, owner, and optional expiry/removal issue. Prompts and knowledge cannot override normative rules.

## 7. Application

The QA workflow freezes scope, maps requirements to checks, verifies gate availability, executes checks, separates baseline/new/resolved/blocker findings, redacts evidence, and records a decision. It must use direct commands until target Make/CI interfaces are actually implemented.

## 8. Repository

Primary artifacts:

- `design/quality-architecture.md`;
- `rules/architecture-boundaries.md`, `rules/quality-gates.md`;
- `.agents/qa-agent.skill.md`;
- `skills/qa-quality-governance/`;
- `tests/_template/quality-gate-result.template.json`.

No generated test result is created during planning. Executed evidence belongs under `tests/results/` and QA reports under `reviews/`.

## 9. API

None. This Spec defines engineering governance and Agent contracts, not an HTTP endpoint.

## 10. Database Impact

None.

## 11. Test Plan

- Validate every referenced path exists and every index points to the canonical file.
- Validate the QA evidence template parses as JSON and contains all required fields.
- Check rule/prompt language does not claim planned targets are active.
- Run `git diff --check` and a link/path review.
- Conduct a dry-run QA plan against one backend-only and one full-stack issue without fabricating results.

## 12. Definition of Done

- [x] Quality design, architecture rules, gate rules, QA skill, knowledge, prompts, and evidence format are reviewed together.
- [x] Normative and explanatory sources have an explicit precedence order and no conflicting gate status vocabulary.
- [x] QA permissions remain read-only for implementation and delivery unless a user explicitly expands scope.
- [x] All artifacts link to AIP-009 and the source review.
- [x] `git diff --check` and JSON template validation pass.

Acceptance evidence: `reviews/AIP-009/governance-acceptance-2026-08-04.md` and `tests/results/*-aip009-dryrun.json` (local-reviewed; delivery not shipped).
