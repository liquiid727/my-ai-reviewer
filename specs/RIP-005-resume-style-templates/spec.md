# RIP-005 - Resume Style Templates

**Status**: Implemented locally (route and empty state only)
**Depends on**: RIP-004
**Scope**: Frontend navigation placeholder

## Goal

Add a dedicated entry for visual resume style templates under the resume module. The first slice only establishes the route and empty state so future style templates can be added without coupling them to the existing reference-content templates.

## Contract

| Item | Contract |
|---|---|
| Entry | A fourth item in the resume module navigation: `简历样式模板` |
| Route | `/resumes/style-templates` |
| Empty state | Show `暂无简历样式模板` when no style templates are available |
| Data source | None in this slice; do not reuse the reference-template API |
| Future extension | Style template records may later provide preview, name, description, tags, and a builder template identifier |

## Out of Scope

- Style template persistence or management
- Preview assets or template cards
- Applying a style template to a resume draft
- Backend API or database changes

## Acceptance Criteria

- The new entry is visible beside the existing resume tabs.
- Activating the entry navigates to `/resumes/style-templates`.
- The route renders the empty state without a network request.
- The existing upload, draft, and reference-template flows remain unchanged.
- Chinese and English translations are present.
