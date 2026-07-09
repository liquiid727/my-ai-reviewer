# GoalSpec

`GoalSpec` is the workflow-driven operating mode for this project.

Use it when:

- the team wants a repeatable plan/design/split/implement/review/ship loop
- issues should stay small enough for a single `/goal` run
- review and ship gates matter, but full role-separated QA/audit governance does not (yet)

Core shape:

```text
project/
  README.md
  docs/spec-modes/
  docs/workflow.md
  current/
  design/
  specs/
    roadmap.md
    issues/
      README.md
    RP-001-example/
      spec.md
      tasks.md
      tests.md
      review.md
      changelog.md
  implementation/
  .agents/
```

Six-step loop:

```
/prd -> /prd-to-spec -> /to-issues -> /goal -> /review-it -> /ship-it
```

Recommended agent loading order:

1. `README.md`
2. `current/`
3. `design/`
4. `specs/issues/`
5. `specs/RP-xxx/`
