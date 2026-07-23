# Frontend Progress

Tracks milestone-level progress for the `frontend/` web app (`feature/web-frontend` branch).
Backend progress is tracked separately in `docs/IMPLEMENTATION_STATUS.md`.

## Completed

### Milestone: Project scaffold + core architecture
- Vite + React 19 + TypeScript (strict) + Tailwind v4 + React Router + TanStack Query +
  React Hook Form + Zod + Vitest + Testing Library + Playwright, in `frontend/`.
- RTL Arabic shell, Tajawal font, design tokens informed by the approved Base44 reference
  site's own public CSS/logo (not copied code).
- Centralized API client (`src/api/client.ts`) with bearer-token auth, single-flight
  401-refresh-and-retry, timeout handling; token storage service (`src/services/tokenStore.ts`
  — access token in memory, refresh token in `sessionStorage`); Arabic error mapping
  (`src/utils/errorMessages.ts`) for every required HTTP status.
- Files: `frontend/{package.json,vite.config.ts,vitest.config.ts,playwright.config.ts,
  tsconfig*.json,.env.example,src/**}`.

### Milestone: Full page set connected to the real backend
- All 24 pages wired into `src/routes/router.tsx`: public (landing/about/how-it-works
  /privacy/disclaimer/login/register/404/error) + authenticated (dashboard, child CRUD,
  assessment intro→take→result, report+PDF, weekly plan incl. mark-complete/alternative
  activity, follow-up/reassessment, assessment/report history, profile incl. logout/delete
  account).
- No hardcoded/fake data in the main flow — every page reads from and writes to the live
  FastAPI backend via the centralized API service.

### Milestone: Backend CORS fix (pre-approved, minimal)
- `backend/.env` / `backend/.env.example`: `CORS_ORIGINS` changed from the unused
  `localhost:3000` placeholder to `127.0.0.1:5173`/`localhost:5173` (the Vite dev server).
  No Python code changed. Covered by `backend/tests/test_cors.py` (3 tests). Documented in
  `docs/DECISIONS_AND_ASSUMPTIONS.md`.

### Milestone: Automated test coverage
- 100 unit/component tests (Vitest + Testing Library + MSW) — Zod schemas, API client
  request/error/refresh-retry matrix, token storage, error mapping, Arabic date/number
  formatting, answer-mapping helpers, and component behavior across
  loading/error/empty/success states for the core pages.
- Backend: 161/161 pytest passing (158 pre-existing + 3 new CORS tests).
- 15 Playwright E2E spec files written covering the 10 required cases (register/login;
  ages 2/3/4/5; mixed, all-yes, all-no answers; unsupported age; invalid input; follow-up
  + reassessment) plus RTL/responsive/focus, offline/server-error/refresh/expired-session
  /logout, and non-diagnostic-wording coverage.

## In progress

- Running the full Playwright E2E suite against the live backend (`:8000`) and frontend dev
  server (`:5173`) for the first time; fixing any failures found.

## Commands run

```bash
# Backend
cd backend && source .venv/Scripts/activate && python -m pytest -q   # 161 passed
# Frontend
cd frontend && npm run typecheck && npm run lint && npm run test     # clean / clean / 100 passed
npm run build                                                        # succeeds
```

## Current errors / blockers

None known as of this update. E2E suite execution is the next actual verification step.

## Next step

1. Run `npx playwright test` (all projects: desktop/tablet/mobile) against the live servers.
2. Fix any failing E2E specs.
3. Write `frontend/README.md`, `docs/FRONTEND_ARCHITECTURE.md`,
   `docs/FRONTEND_API_INTEGRATION.md`, `docs/FRONTEND_TEST_PLAN.md`,
   `docs/FRONTEND_MANUAL_TEST_CASES.md`.
4. Final verification pass (build, full test suite, RTL, responsive, secrets scan).
