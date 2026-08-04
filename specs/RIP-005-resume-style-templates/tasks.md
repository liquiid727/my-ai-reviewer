# RIP-005 Tasks

## T1 - Route and navigation (completed)

- Add `/resumes/style-templates` to the frontend router.
- Add the fourth resume-module navigation entry.
- Keep the global resume navigation active on the new route.

## T2 - Empty-state page (completed)

- Add the standalone style-template page.
- Reuse existing tabs, card, button, icon, spacing, and border tokens.
- Keep the page data-free until a style-template contract is approved.

## T3 - Verification (partially completed)

- [x] Run frontend build and lint.
- [x] Confirm both SPA entry URLs return `200` from the local dev server.
- [ ] Manually verify `/resumes`, the new route, the empty state, and language switching in a browser.

The browser check is pending because the current browser session denied access to the local development URL.
