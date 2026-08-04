# Frontend Architecture

**Status**: Active as-built baseline

**Last Updated**: 2026-08-04

**Runtime**: React 19, TypeScript, Vite, React Router, Zustand, Tailwind CSS, Radix UI primitives, Lucide icons, Recharts, Sonner, and i18next.

The frontend is a client-rendered SPA under `frontend/`. It is not a Next.js application. Vite produces static assets; the browser calls the FastAPI backend under `/api/v1`.

## 1. Application Composition

```text
frontend/src/main.tsx
  |
  +-- i18n/config + index.css
  +-- App.tsx
        |
        +-- BrowserRouter
        +-- Layout
              |
              +-- page route
                    |
                    +-- page-local UI state and effects
                    +-- feature API module (src/api/*.ts)
                    +-- feature store when state spans pages
                    +-- shared components and ui primitives

src/api/client.ts -> /api/v1 -> FastAPI
vite.config.ts    -> /api proxy to http://localhost:8000 in development
```

The frontend uses a feature-by-convention structure rather than a separate domain package. Pages are the primary composition boundary, API files are the transport boundary, stores hold cross-page client state, and components provide reusable interaction or presentation units.

## 2. Directory Responsibilities

| Path | Responsibility |
|---|---|
| `frontend/src/main.tsx` | Browser bootstrap, StrictMode, i18n and global CSS initialization |
| `frontend/src/App.tsx` | Route table and application-level toaster |
| `frontend/src/components/Layout.tsx` | Global navigation, responsive shell, builder full-bleed mode, nested route outlet |
| `frontend/src/pages/` | Route-level screens and feature workflow orchestration |
| `frontend/src/components/` | Reusable feature components such as upload, LLM gate, JD editor, plan task editor, assistant panel, and export dialog |
| `frontend/src/components/ui/` | Local Radix/shadcn-style primitives and variant definitions |
| `frontend/src/api/` | Typed request functions grouped by backend resource |
| `frontend/src/types/` | TypeScript representations of API and UI data contracts |
| `frontend/src/stores/` | Zustand stores for resume upload/history, interview state, and LLM settings |
| `frontend/src/i18n/` | i18next setup, formatting helpers, and Chinese/English locale resources |
| `frontend/src/lib/` | Small shared helpers and provider metadata |
| `frontend/src/index.css` | Tailwind import and project design tokens |
| `frontend/vite.config.ts` | React/Tailwind plugins, `@` alias, and local API proxy |

## 3. Route Map

`frontend/src/App.tsx` is the route source of truth.

| Route | Page | Primary workflow |
|---|---|---|
| `/` | redirect | Redirect to upload |
| `/upload` | `UploadPage` | File selection, LLM gate, upload, polling, retry |
| `/resumes` | `MyResumesPage` | Resume history and selection |
| `/resumes/style-templates` | `ResumeStyleTemplatesPage` | Reference builder templates |
| `/resume/:id` | `ResumePage` | Parsed resume detail, interview/builder entry points |
| `/resume/:id/evaluation` | `EvaluationPage` | Resume evaluation result |
| `/interviews` | `InterviewListPage` | Interview history |
| `/interview/:id` | `InterviewPage` | Question, answer, evaluation, follow-up loop |
| `/interview/:id/report` | `InterviewReportPage` | Completed interview report |
| `/jobs` | `JDListPage` | JD library, search, filtering, import |
| `/jobs/:id` | `JDDetailPage` | JD extraction, edit, match, retry/re-extract |
| `/plans` | `PlanListPage` | Job-search plan list, search, status filter |
| `/plans/new` | `PlanCreatePage` | Select JD/resume and start plan generation |
| `/plans/:id` | `PlanDetailPage` | Plan tasks, mutation, regeneration, revision conflict |
| `/builder/:draftId` | `BuilderPage` | Full-bleed resume editing, AI assistant, preview/export/photo |
| `/settings` | `SettingsPage` | LLM provider configuration and verification |

`Layout` is shared by all routes. Builder routes use a full-bleed workspace and a collapsible navigation affordance; other routes use the constrained application shell.

## 4. API and Type Boundaries

API modules are grouped by backend resource:

| Frontend module | Backend resource | Shared concerns |
|---|---|---|
| `api/resume.ts` | `/api/v1/resume` | Upload, status, privacy review, parsed facts/profile |
| `api/evaluation.ts` | `/api/v1/resume/{id}/evaluation` | Resume evaluation |
| `api/interview.ts` | `/api/v1/interview` | Create/start/answer/status/report/list |
| `api/jd.ts` | `/api/v1/jd` | Import, list/detail, edit, extraction, matching |
| `api/plans.ts` | `/api/v1/plans` | Generation, list/detail, task CRUD/order |
| `api/builder.ts` | `/api/v1/builder` | Drafts, assistant proposals, polish/score, preview/export/photo |
| `api/settings.ts` | `/api/v1/settings/llm` | LLM configuration and connection test |

`api/client.ts` owns the standard JSON request path:

- base URL: `/api/v1`;
- JSON `Content-Type` is added unless the body is `FormData`;
- non-2xx responses become `ApiRequestError` with HTTP status, optional backend code, and data;
- successful responses are returned as the typed `APIResponse` shape defined in `src/types/`.

Builder assistant calls have a specialized request helper because they expose proposal-specific error details. Binary PDF export uses `fetch`, response headers, and a `Blob` rather than the JSON envelope. These exceptions should stay isolated to their feature module.

## 5. State Management

The frontend uses two levels of state:

### Page-local state

`useState`, `useEffect`, and `useCallback` handle loading/error/empty state, form fields, dialogs, mutation pending state, polling, and route-specific data. Pages should own state that is not needed after navigation.

### Zustand stores

| Store | Responsibility |
|---|---|
| `resumeStore` | Current upload ID, processing status, step progress, and failure state |
| `resumeHistoryStore` | Resume list/history data and refresh behavior |
| `interviewStore` | Current interview question/answer interaction state |
| `settingsStore` | LLM configs, loaded state, and refresh after create/update/delete/test |

There is no React Query/SWR cache or global event bus. A mutation that affects another route should explicitly refresh or update the relevant store. Avoid adding a second caching strategy without documenting invalidation behavior.

## 6. User-Visible State Contract

Every data-backed page should make these states explicit:

| State | Current pattern |
|---|---|
| Loading | Skeletons, disabled controls, progress indicators, or loading labels |
| Empty | Empty-state copy and a next action, such as upload/create/import |
| Success | Render typed data and expose the next workflow action |
| Failure | Alert/toast with a retry or recovery action where possible |
| Mutation pending | Disable duplicate actions and show progress/feedback |
| Conflict/expired state | Reconcile or ask the user to reload, especially for Builder revisions, plan revisions, and privacy TTL |

Upload polling and plan generation are state machines rather than generic spinners. Polling must stop on terminal success/failure, surface timeout, and avoid continuing after the page no longer owns the request.

## 7. UI and Interaction Design

- Tailwind CSS 4 tokens are defined in `src/index.css`.
- Reusable primitives live in `src/components/ui/` and are based on Radix UI patterns.
- The visual language uses a restrained neobrutalist treatment: strong borders, hard shadows, compact cards, and explicit status badges.
- Lucide icons are used for recognizable actions; unfamiliar icon buttons require a title/tooltip.
- Forms should use controls that match the value type: file dropzone for files, select for enumerations, stepper/input for numbers, and dialogs for confirmation or focused editing.
- User-facing copy goes through `useTranslation` and locale resources instead of being embedded in feature components.
- Responsive behavior belongs in layout/component classes; route pages should not rely on a fixed desktop width.

## 8. Development and Build

```text
cd frontend
pnpm install
pnpm dev       # Vite development server; /api proxies to localhost:8000
pnpm build     # TypeScript project build + Vite production build
pnpm lint      # Oxlint
pnpm preview   # Preview the production bundle
```

The frontend currently has no test script in `package.json`. Browser verification is described by feature specs and can be run through the repository's browser/playwright tooling when a feature requires it. `dist/` is a generated artifact and is not the source of truth.

## 9. Frontend/Backend Contract Rules

- Keep route paths and response names aligned with `backend/api/v1/` and the feature spec that introduced them.
- Do not expose raw backend error objects directly in user-facing copy; map them to translated, actionable messages.
- Treat `APIResponse.code` and HTTP status independently: a successful HTTP response may still contain a business error code.
- Preserve server-controlled fields. For example, Builder photo references are written by dedicated confirm/delete routes, not arbitrary draft identity updates.
- Include revision/base-revision values in concurrency-sensitive mutations and provide a reconciliation path for conflicts.
- Long-running backend work should be represented by a visible frontend status and a retry/reload action.
- Privacy-sensitive flows must display masked content only and must never reconstruct raw values in browser state unless a feature spec explicitly defines a controlled local operation.

## 10. Known Gaps and Assumptions

- There is no authentication or route guard in the SPA; all routes assume the local development user context.
- API types are maintained manually rather than generated from OpenAPI, so backend contract changes require a coordinated frontend type update.
- The frontend does not yet expose a complete privacy-review route matching all RIP-009 API operations; the upload and review UI remains a feature-level delivery concern.
- Polling is implemented by pages/stores rather than a shared request-state library. New polling flows should follow the existing terminal-state and cleanup patterns.
- `frontend/package.json` still uses the temporary package name `frontend-tmp`; renaming it is a packaging decision, not an architecture requirement.
- Vite proxy configuration is local-only. Production must provide a same-origin reverse proxy or an explicit API base URL and CORS policy.
- The architecture image includes RAG stages that have no active frontend route yet. UI for those stages belongs in a feature spec after the backend contract exists.
