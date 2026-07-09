# LiteSpec

`LiteSpec` is the default operating mode for this project.

Use it when:

- one engineer or one agent can finish a feature end to end
- low-token context matters
- feature isolation matters more than formal delivery evidence

Core shape:

```text
project/
  README.md
  docs/spec-modes/
  current/
  design/
  specs/
    roadmap.md
    _draft/
    RP-001-example/
      spec.md
      tasks.md
      tests.md
      review.md
      changelog.md
  .agents/
```

Recommended agent loading order:

1. `README.md`
2. `current/`
3. `design/`
4. `specs/RP-xxx/`
5. the relevant skill file
