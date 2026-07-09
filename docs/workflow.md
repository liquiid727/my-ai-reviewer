# GoalSpec Workflow

GoalSpec runs the six-step goal loop as the project's standard delivery chain:

```
/prd -> /prd-to-spec -> /to-issues -> /goal -> /review-it -> /ship-it
```

| Step | Command | Output |
| --- | --- | --- |
| Plan | `/prd` | PRD in `spec-draft/` |
| Design (optional) | `/prd-to-spec` | Updated `design/` |
| Split | `/to-issues` | Issue entries in `specs/issues/README.md` and `specs/RP-xxx/tasks.md` |
| Implement | `/goal` | Feature landed in `specs/RP-xxx/`, changed-surface summary in `implementation/` |
| Review | `/review-it` | `specs/RP-xxx/review.md` |
| Ship | `/ship-it` | Commit, PR, merge, `specs/RP-xxx/changelog.md`, issue closed |

`/prd-to-spec` and `/to-issues` are optional for small features; skip straight from `/prd` to `/goal` when a feature is a single obvious issue.

Batch multiple issues with `/loop-it` when several independent issues are ready to run back to back.
