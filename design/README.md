# Design

`design/` is the canonical home for stable platform and system design. These documents describe the current implementation baseline and the constraints that feature specifications must respect.

Feature-specific behavior belongs in `specs/`, not in a second architecture document. When implementation and design differ, record the gap in the relevant feature spec or update the design with the decision and its scope.

## Architecture Documents

| Document | Scope |
|---|---|
| [architecture.md](architecture.md) | System-level architecture, runtime components, cross-cutting rules, and current/target boundary |
| [backend-architecture.md](backend-architecture.md) | FastAPI modular monolith, application/domain/infrastructure layers, workers, and backend workflows |
| [frontend-architecture.md](frontend-architecture.md) | React/Vite SPA, routes, pages, components, API clients, stores, and UI state rules |
| [domain.md](domain.md) | Domain concepts and interview workflow model |
| [database.md](database.md) | Relational entities, relationships, and schema extensions |
| [api-guidelines.md](api-guidelines.md) | API naming, response envelopes, error conventions, and core business flow |
| [deployment.md](deployment.md) | Local infrastructure, service dependencies, and operational configuration |
| [coding-guidelines.md](coding-guidelines.md) | Layering, typing, FastAPI, and workflow coding conventions |
| [quality-architecture.md](quality-architecture.md) | Target quality governance baseline (AIP-009–012): ownership, boundaries, gates, errors, logging, rollout — not pure as-built |

## Documentation Rules

- Keep one canonical document per stable system or concern.
- Prefer as-built behavior over aspirational diagrams, and label planned capabilities explicitly.
- Link feature specs to these documents instead of copying architecture sections into every feature.
- Update the design when a change alters a cross-feature boundary, data contract, runtime dependency, or operational assumption.

## Repository Layout

```text
design/
  architecture.md
  backend-architecture.md
  frontend-architecture.md
  domain.md
  database.md
  api-guidelines.md
  deployment.md
  coding-guidelines.md
  quality-architecture.md
  _template/
```
