# Deployment readiness report

Date: 2026-08-01
Target: public beta/demo deployment using Netlify + Render + Neon PostgreSQL

## Implemented

### Persistent hosted database

- Added `asyncpg` for hosted PostgreSQL.
- Normalized common Neon/PostgreSQL URLs to `postgresql+asyncpg`.
- Translated `sslmode` to asyncpg's `ssl` option and removed `channel_binding`.
- Added production fail-closed checks: PostgreSQL only, strong random secret, and exact HTTPS
  CORS origins.
- Added connection pre-ping and hosted connection recycling.
- Escaped percent-encoded database URLs for Alembic's ConfigParser.

### Durable weekly reassessment

- Added Alembic revision `9c7e4d12a6b1`.
- Persisted frozen AI/deterministic follow-up questions, generation source, fallback reason,
  and freeze timestamp on `weekly_plans`.
- Used an atomic first-writer-wins update so concurrent requests/workers return the same set.
- Added backend `reassessment_started` state so “متابعة إعادة التقييم” survives refreshes,
  tabs, process restarts, and deployment restarts.

### Hosting UX and configuration

- Added `netlify.toml` with Vite build settings, SPA redirect, asset caching, and security
  headers.
- Added `render.yaml` with Python runtime, migrations-before-start, readiness checks, and
  secret placeholders.
- Added `.python-version` pinned to Python 3.13.
- Added an Arabic backend cold-start gate that probes `/health`, waits through a bounded hosted
  wake window, and offers a manual retry.
- Added `docs/DEPLOYMENT.md` with the complete deployment order and environment variables.

### Docker hardening

- Added root `.dockerignore` so secrets, databases, virtual environments, Node dependencies,
  logs, reports, screenshots, and test artifacts cannot enter the build context.
- Updated the backend Dockerfile to build from repository root, include the knowledge base,
  run as a non-root user, apply migrations, and expose a readiness health check.
- Updated Docker Compose to use the repository-root Dockerfile and readiness check.

### Manual-test defects addressed

- Alternative activity requests are deduplicated in the frontend.
- When the unused same-domain pool is exhausted, the backend can reuse a different approved
  same-domain activity instead of returning an unavoidable 409.
- Activity replacement is disabled and backend-blocked once reassessment questions are frozen,
  preserving question/activity grounding.
- Arabic PDF rendering now sanitizes directional/control characters, embeds the packaged
  Tajawal font, wraps shaped RTL lines, uses structured sections, and adds page footers.


### Account cache privacy isolation

- Confirmed that the cross-account display was stale TanStack Query data because a hard refresh
  immediately restored the correct account data.
- Updated `AuthProvider` to clear the complete query and mutation cache on successful login,
  logout, failed session restoration, refresh/session expiry, and account deletion.
- The cache is cleared before a newly authenticated account is rendered, preventing any child,
  assessment, report, weekly-plan, follow-up, or AI-response data from the previous account from
  appearing in the new session.
- Added focused regression tests for login-account switching and logout cache removal.

### CI and documentation

- Expanded GitHub Actions to verify backend and frontend separately.
- Added deployment/configuration tests and updated architecture, API, security, database,
  RAG/AI, test-plan, progress, and milestone documentation.

## Verification completed in the sanitized review environment

- Python syntax compilation succeeded for backend application, Alembic migrations, tests, and
  scripts.
- TypeScript/TSX syntax transpilation succeeded for 132 files.
- The complete TypeScript project typecheck (`tsc -b`) succeeded after the account-cache fix.
- `netlify.toml` and `render.yaml` parsed successfully.
- Production settings smoke checks confirmed safe PostgreSQL/CORS/secret acceptance and
  rejection of SQLite, weak secrets, and wildcard CORS.
- Knowledge-base validation succeeded for 591 normalized KB01-KB05 records.
- Migration revision-chain inspection confirmed a single head ending at `9c7e4d12a6b1`.
- Secret/artifact scanning is performed again before packaging.

## Verification limitation

The sanitized review environment does not contain all project dependencies and its internal
package registry could not supply several required packages, including `asyncpg`,
`arabic-reshaper`, `python-bidi`, `google-genai`, and the locked frontend package set.
Therefore the complete Pytest, Mypy, Ruff, Vitest, frontend production build, Playwright,
real PostgreSQL migration, and rendered-PDF visual inspection must be rerun in the user's full
local environment before commit and deployment. The TypeScript project typecheck was completed
successfully in this review.

Use the exact commands in `docs/DEPLOYMENT.md`. Do not publish if a critical test, migration,
typecheck, or build fails.

## Excluded from this package

- Real `.env` files
- API keys and secrets
- SQLite databases
- `.git` history
- Python virtual environments
- `node_modules`
- build output
- logs, generated reports, screenshots, traces, and videos
- test caches and temporary outputs
