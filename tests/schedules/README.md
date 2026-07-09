# Test Schedules

Generated `test-schedule` artifacts live here.

Schedules are machine-readable task-layer artifacts. They split one active spec change into isolated work tracks:

- `execution`: implementation work plus implementation-coupled unit tests.
- `testing`: spec-and-contract-only API, E2E, UI, and business scenario verification.

The schedule is generated from `spec.md` through:

```bash
node packages/cli/dist/main.js generate-test-plan specs/RP-002-decision-api/spec.md --change RP-002
```

JSON companions may still exist for compatibility, but the preferred contract path is now the frontmatter inside `spec.md`.

The independent test console still consumes normalized files from `tests/results/`; schedules describe agent routing and execution boundaries before those results exist.
