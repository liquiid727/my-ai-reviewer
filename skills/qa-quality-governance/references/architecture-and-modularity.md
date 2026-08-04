# Architecture And Modularity Knowledge

## Review Model

Review architecture as dependency ownership, not folder names. A file under `domain/` that imports an ORM model is infrastructure-coupled even if the runtime behavior is correct. A new `ports.py` file is not decoupling until callers depend on the port and construction moves to a composition root.

For each changed workflow, write the actual chain:

```text
entry -> orchestration -> policy -> side-effect boundary -> result mapping
```

Then verify that each owner is in the intended layer and that dependencies point inward toward contracts.

## Incremental Extraction Sequence

1. Add characterization tests around the current public behavior and failure branches.
2. Identify one reason to change and define a typed use-case input/result.
3. Define the narrow port needed by that use case; avoid mirroring an entire SDK or ORM.
4. Adapt the existing implementation behind the port.
5. Wire it at the composition root and switch one caller.
6. Run contract, behavior, and architecture checks.
7. Remove the old path or add an expiring compatibility issue.

This is safer than moving all domain services, routers, and models at once.

## Pattern Selection

- Use a Strategy when implementations vary at runtime behind one stable behavior, as parsers and LLM providers already do.
- Use a Factory when selection/construction logic would otherwise leak to callers.
- Use a Protocol port when core orchestration must call an external capability.
- Use an Application Service or command handler when a route/task coordinates state, persistence, and side effects.
- Use an anti-corruption adapter when provider errors or payloads differ from project contracts.
- Use a state machine when transitions, retries, terminal states, or stale ownership are business-relevant.
- Use a Facade only to expose cohesive use cases. Reject facades that merely accumulate unrelated methods.
- Reject a generic repository until multiple aggregates share meaningful semantics beyond CRUD syntax.

## Decomposition Evidence

Good evidence includes fewer forbidden imports, a smaller constructor dependency set, independently testable policies, one transaction owner, eliminated duplicate error/polling logic, and narrower fixtures. File length can identify a hotspot but is not proof of improvement.

For Builder and Resume work, pay special attention to hidden coupling among ORM models, privacy, MinIO, rendering, LLM, revision checks, and API serialization. Extract by use case, not by arbitrary helper category.

## Directory Review

- Confirm each new directory has one named owner and consumers.
- Confirm empty extension points are labeled planned and excluded from runtime diagrams.
- Confirm model splits still load full SQLAlchemy metadata in application startup and Alembic.
- Confirm frontend feature modules do not create a second API client/type source.
- Confirm compatibility re-exports have a removal path.
