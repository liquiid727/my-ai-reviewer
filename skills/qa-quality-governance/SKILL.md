---
name: qa-quality-governance
description: Project-local QA workflow for architecture compliance, quality gates, error/logging review, evidence normalization, and merge/release decisions.
---

# QA Quality Governance

Use this skill for project-wide audits, feature QA, CI gate verification, architecture-boundary review, refactoring verification, and error/logging assessments in this repository.

## Authority

Read and apply sources in this order:

1. The current user request and repository `AGENTS.md`.
2. `.agents/qa-agent.skill.md` for role permissions and the QA report contract.
3. `rules/architecture-boundaries.md` and `rules/quality-gates.md` for normative requirements.
4. `design/quality-architecture.md` for rationale and target shape.
5. The active feature Spec/test contract and the task-specific references below.

Knowledge pages explain review reasoning; they do not override rules. Prompt templates are entry aids; they do not authorize writes, merge actions, or threshold changes.

## Modes

| Mode | Use when | Required output |
|---|---|---|
| `change-gate` | reviewing a diff or issue implementation | feature QA report + exact gate results |
| `architecture-audit` | reviewing dependencies, directories, or decomposition | findings with rule IDs and dependency evidence |
| `error-observability` | reviewing errors, logs, correlation, retries, or PII | public/internal contract matrix + privacy evidence |
| `project-baseline` | measuring repository-wide quality | project QA report + baseline/new/resolved split |
| `release-gate` | deciding whether reviewed work may ship | reproducible required-check matrix and decision |

## Knowledge Routing

- Architecture, module split, ports, adapters, repositories, state machines: read `references/architecture-and-modularity.md`.
- Tests, Make targets, CI, skips, coverage, evidence formats: read `references/testing-and-gates.md`.
- Errors, HTTP mapping, logging, Celery/LLM context, secrets/PII: read `references/errors-and-observability.md`.

Read only the pages relevant to the scope, but read each selected page completely.

## Workflow

1. Freeze the scope: spec/issue, baseline ref, head/worktree, changed files, external services, and user-authorized writes.
2. Build a requirement-to-gate matrix before executing checks.
3. Inspect gate availability. Never assume a Make target, package script, service, or browser exists.
4. Execute the smallest complete set: changed unit tests first, then required static/contract/integration/browser checks.
5. Separate baseline findings, change-introduced findings, resolved findings, and environment blockers.
6. Apply P0-P3 severity and `PASS/FAIL/BLOCKED/NOT_RUN` exactly as defined by project rules.
7. Check evidence for secrets, direct identifiers, raw resume content, prompt/completion data, and unsafe filenames before saving it.
8. Write the report/result only from observed evidence; finish with a reproducible gate decision.

## Non-Negotiable Checks

- No new architecture exception, ignore, skip, `xfail`, coverage exclusion, or threshold reduction without owner, reason, expiry, and removal issue.
- An assertion failure is `FAIL`, not `BLOCKED`.
- A missing database can block an integration test, but a test that silently skipped because the database was missing is not integration evidence.
- A large-file split passes only when responsibilities/dependencies improve and characterization tests remain green.
- Public errors never contain raw causes; internal error evidence stays redacted.
- Logs and report artifacts use synthetic identifiers and content.

## Prompt Registry

- `prompts/project-quality-audit.md`: repository-wide baseline or follow-up audit.
- `prompts/change-gate-review.md`: one Spec/issue implementation gate.
- `prompts/refactoring-slice-review.md`: behavior-preserving modularization review.
- `prompts/error-observability-review.md`: error/logging/correlation/privacy review.

Replace placeholders before use. A prompt result still requires source inspection and executed checks.
