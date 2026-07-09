# Current

`current/` is the active delivery workspace.

Use it to keep only the context agents and engineers need right now:

- project status
- active feature
- active context
- active tasks
- blockers
- handoff notes

Recommended `LiteSpec` shape:

```text
current/
  project-status.md
  active-feature.md
  active-context.md
  active-tasks.md
  blockers.md
  handoff.md
```

Recommended `EnterpriseSpec` shape:

```text
current/
  release-status.md
  sprint-status.md
  active-feature.md
  blockers.md
  decisions.md
  handoff.md
```

Do not turn `current/` into a second archive. It should stay small, current, and replaceable.
