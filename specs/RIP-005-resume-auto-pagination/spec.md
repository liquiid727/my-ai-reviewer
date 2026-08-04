# RIP-005 - Resume Auto Pagination

**Version**: v1.0
**Status**: In Review
**Depends on**: RIP-004

## Goal

Replace the one-page-only layout switch with deterministic automatic pagination.
The editor preview and exported PDF must use the same rendering result and may
contain any number of A4 pages.

## Layout Policy

- `auto_pages`: choose the smallest page count available within the supported
  density range, then choose the loosest density that produces that count.
- `target_pages`: try to produce the requested page count, choosing the loosest
  matching density. If no density matches, export the automatic result and mark
  the target as unmet.
- `target_page_count` is required only for `target_pages` and is limited to 1-10.
- The editor exposes `target_page_count` as a directly editable numeric stepper;
  invalid values are not persisted.
- The legacy `auto_one_page` field is removed without compatibility handling.

## Rendering Contract

- A4 is the fixed physical page size.
- Page margins repeat on every printed page.
- Section headings stay with following content. Sections may split between
  items so pages remain filled; items avoid splitting where possible, while
  oversized content may split so it is never clipped.
- Page count comes from the generated PDF, not DOM height estimation.
- Preview returns the same PDF layout used by export.

## LLM Boundary

Pagination does not require an LLM. A future content-fitting agent may use the
active verified LLM configuration to return user-confirmed rewrite suggestions,
but it must not write CSS, choose page coordinates, or mutate a draft silently.

## Acceptance

- Automatic layout produces valid 1, 2, and 3+ page PDFs without overflow being
  treated as an error.
- Target layout reports whether the requested page count was met.
- Preview and export report the same page count and applied density.
- Classic, modern, and compact templates preserve all visible text across pages.
- Backend tests, frontend build/lint, and browser verification pass.
