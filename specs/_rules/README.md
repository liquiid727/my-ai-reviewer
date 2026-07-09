# Spec Rules

This file defines the canonical naming, slicing, and section rules for SpecOS feature specs.

## Naming

- Spec ID format: `<EPIC-CODE>-<3 digit number>` such as `RP-002`
- Feature directory format: `<SPEC-ID>-<slug>` such as `RP-002-decision-api`
- Feature title format: `<SPEC-ID> <Title>` such as `RP-002 Decision API`
- Dependencies must always be listed by spec id

## Slicing

- One feature spec = one small, end-to-end feature slice
- Prefer narrow slices like `Decision API`, not broad buckets like `Decision Engine`
- Do not merge multiple dependencies into one oversized spec; express reuse through `Depends On`
- A design document is broad and singular; feature specs are narrow and numerous

## Required Feature Spec Sections

Use this order exactly:

1. `Meta`
2. `Goal`
3. `Why This Exists`
4. `Out of Scope`
5. `Deliverables`
6. `Domain`
7. `Application`
8. `Repository`
9. `API`
10. `Database Impact`
11. `Test Plan`
12. `Definition of Done`

## Field Rules

- `Meta` must include `Spec ID`, `Title`, `Epic`, `Status`, `Owner Agent`, `Depends On`, and `Prerequisites`
- `Prerequisites` lists upstream identities, contracts, or registry data already provided
- `Deliverables` must be explicit and concrete
- `Database Impact` must say `none` when there is no schema or storage change
- `Definition of Done` must be a checklist, not prose
- `Out of Scope` must explicitly block nearby work that does not belong to the slice
