# Browser Acceptance Waiver — Job Target Interview Program (#092-140)

**Date**: 2026-08-05
**Status**: Active — deferred browser acceptance for the Job Target Interview Program issue run
**Scope**: All browser-based acceptance criteria in issues #092-140 (frontend/fullstack issues)

## Reason

The local environment has no browser automation controller installed:

- `~/.cache/ms-playwright` is empty (no Playwright browser binaries).
- Prior RIP-007/RIP-008 acceptance recorded the same constraint: `reviews/RIP-007-008-2026-08-03.md` returned a `conditional-pass` verdict with browser-required acceptance "blocked by the unavailable local browser controller" (deferred item 4).
- There is no waiver document for that earlier run either; this note formalizes the standing environment limitation.

## What is deferred

For each frontend/fullstack issue that lists browser checks in its acceptance criteria, the **browser-verification sub-items** are deferred. This includes, but is not limited to:

- Desktop/mobile browser layout checks
- Refresh-persistence / deep-link recovery in a real browser
- Multi-tab and browser-concurrency scenarios
- Accessibility (keyboard) verification in a real browser
- Screenshot-based privacy canary scans

## What still runs

All non-browser gates run to completion for every issue:

- Backend: unit + integration tests (`make test-unit`, `make test-integration`), `make lint`, `make type-check` (new errors only), `make arch-check`
- Database issues: Alembic `upgrade head` / `downgrade base` / `upgrade head` + `alembic check`
- Frontend: `pnpm lint`, `pnpm build`, `vitest run`

## Effect on delivery status

Browser-deferred ACs do **not** block the backend/database critical path (#092 → #107 → #117 → #130 → #140). Frontend issues are topologically leaves in the issue graph, so their deferred browser checks never block later backend work. Each affected issue is marked with a "browser AC deferred" note and its evidence JSON records the deferral.

## Re-activation

When a browser controller is available (Playwright binaries installed or a remote browser service reachable), re-run the deferred browser ACs for the affected issues. Re-activation supersedes this waiver for those sub-items.

## References

- `reviews/RIP-007-008-2026-08-03.md` — prior conditional-pass with the same browser limitation
- `design/quality-architecture.md` § waiver policy
- Issues affected: the 8 UI/close issues (#096, #101, #105, #114, #120, #127, #133, #139) and the 6 acceptance-close issues (#102, #106, #115, #121, #128, #134, #140)
