# Frontend

The frontend is a React 19 + TypeScript + Vite single-page application. It communicates with the FastAPI backend under `/api/v1`; Vite proxies `/api` to `http://localhost:8000` during local development.

The canonical frontend design document is [`design/frontend-architecture.md`](../design/frontend-architecture.md). The system-level and backend documents are available from [`design/architecture.md`](../design/architecture.md) and [`design/backend-architecture.md`](../design/backend-architecture.md).

## Run Locally

```text
pnpm install
pnpm dev
pnpm build
pnpm lint
pnpm preview
```

## Source Layout

```text
src/
  api/          typed backend request modules
  components/   shared feature components and UI primitives
  i18n/         Chinese/English translations and formatting
  lib/          shared helpers and provider metadata
  pages/        route-level screens
  stores/       Zustand cross-page state
  types/        API and UI TypeScript contracts
  App.tsx       route table
  main.tsx      browser bootstrap
```

`dist/` is generated output. Feature-level behavior and acceptance criteria belong in `specs/` and `tasks/issues/`, not in this README.
