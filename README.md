# Smart Guide for Children's Language Delay

An Arabic-first web application that gives parents supportive, evidence-based guidance
about early language development for children aged 2–5.

> This application is a decision-support tool. It does not diagnose a child and does not
> replace assessment or treatment by a qualified Speech-Language Therapist.

## Current implementation

- Web frontend: React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, and Playwright.
- Backend: FastAPI, SQLAlchemy, and Alembic; SQLite for local development and PostgreSQL for hosted deployment.
- Knowledge base: the approved KB01–KB05 workbooks plus the structured, deterministic
  `knowledge_base/KB06.json` weekly-follow-up source.
- Assessment scoring, specialist-referral decisions, reports, and weekly plans are currently
  deterministic and knowledge-base driven.
- Optional server-side Gemini wording assistance is implemented for assessment/plan/follow-up
  summaries, grounded weekly follow-up wording, and per-activity explanations. It is disabled
  by default and every operation has a deterministic fallback.

The implemented MVP includes parent authentication, child profiles, initial assessment,
results, reports/PDF, weekly plans, weekly follow-up, progress comparison, and persisted
data after reload/login.

### Weekly follow-up workflow

Initial assessment and weekly follow-up are separate flows. KB05 remains the broad,
age-appropriate initial assessment. After at least 70% of the current active plan activities
are complete, the parent can open a plan-linked weekly follow-up containing 5–8 deterministic
KB06 questions matched to the child's age, plan domains, goals, and approved KB02 activities.
Submitting once stores the answers and weekly progress, deactivates the completed plan, and
creates the next active plan through the existing deterministic plan service. Retries are
idempotent, and ownership is checked through the child and exact weekly plan.

Arabic PDF reports use the packaged SIL Open Font License Tajawal asset, Arabic shaping, and
bidirectional layout. The font is embedded in each PDF, so Arabic output does not depend on a
private font installed on the host machine.

## Local Windows setup

Use two PowerShell terminals.

Backend:

```powershell
cd "C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub\backend"
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd "C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub\frontend"
npm install
npm run dev
```

Expected local URLs:

- Backend: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`
- Frontend: the URL printed by Vite, normally `http://localhost:5173`

See [MANUAL_FRONTEND_TESTING_GUIDE.md](MANUAL_FRONTEND_TESTING_GUIDE.md) for the complete
manual flow and troubleshooting.


## Beta deployment

The repository includes production-oriented deployment configuration for:

- Netlify: React/Vite static frontend with SPA redirects (`netlify.toml`).
- Render: FastAPI web service with health checks and Alembic migration startup (`render.yaml`).
- Neon: persistent PostgreSQL through `DATABASE_URL`.

The frontend includes an Arabic cold-start gate for a sleeping free Render backend. Frozen
weekly reassessment questions are stored in the database, and hosted PostgreSQL URLs are
normalized for SQLAlchemy asyncpg. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the exact
setup, environment variables, safety checks, and post-deploy test flow.

## Verification commands

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd frontend
npm run test
npm run typecheck
npm run lint
npm run build
```

The E2E runner is intentionally isolated from manual development. It uses backend port
`8001`, frontend port `4173`, and `backend/language_delay_e2e.db`. Do not use the E2E
launcher or port 8001 for manual testing.

## Important files

- `CLAUDE.md` and `AGENTS.md` — agent workflow and safety instructions.
- `PROJECT_SPEC.md` — approved product requirements.
- `PROJECT_STATUS_AND_MILESTONES.md` — current milestone status.
- `PROGRESS.md` — latest agent handoff and verification record.
- `MILESTONE_1_STABILIZATION_REPORT.md` — Milestone 1 regression report.
- `MILESTONE_2_GEMINI_PROPOSAL.md` — approved design and safety boundary.
- `MILESTONE_2_GEMINI_IMPLEMENTATION_REPORT.md` — implementation and verification record.
- `knowledge_base/` — approved KB01–KB05 scientific content (read-only) and the structured
  KB06 weekly-follow-up source.
- `backend/assets/fonts/` — packaged Tajawal font and its SIL OFL redistribution license.

## Secrets and generated data

Never commit `.env` files, API keys, tokens, passwords, SQLite databases, generated PDFs,
`node_modules`, build output, logs, screenshots, traces, videos, Playwright artifacts, or
temporary files. Use example environment files as templates and keep real values local.

## Optional Gemini-assisted wording

Milestone 2 adds three optional server-side assistance endpoints for:

- a parent-friendly explanation of a completed assessment;
- a summary of an already-generated weekly plan;
- a summary of an already-computed weekly follow-up.

The deterministic backend remains authoritative for scoring, severity, referral,
eligibility, activities, plans, and progress. Gemini cannot change those values. The
backend sends only minimized age-band, deterministic, and approved KB facts; it never sends
names, emails, user/child/resource IDs, tokens, answer history, notes, or medical history.
Every provider response must pass strict JSON, safety, grounding, and immutable-fact
validation. Any disabled, unavailable, timed-out, invalid, unsafe, or ungrounded response
returns useful deterministic wording with HTTP 200.

Gemini is disabled by default. Install backend dependencies from `requirements.txt`, then
configure local values in `backend/.env` (never commit that file):

```powershell
Set-Location .\backend
Copy-Item .env.example .env
# Edit only the local .env:
# GEMINI_ENABLED=true
# GEMINI_API_KEY=<your key>
# GEMINI_MODEL=<model available to your Google AI project>
```

The model is intentionally configuration-only; the repository does not hardcode or
automatically select one. Disable the feature instantly with `GEMINI_ENABLED=false`.

## Milestone 3 — AI-guided weekly reassessment, activity explanations, source UX

Builds on Milestone 2's provider-neutral AI architecture with two more optional, always-
deterministic-fallback features, plus one new deterministic rule and a UX fix:

- **70% reassessment eligibility** (replaces the old 100%-only rule): a parent may start the
  weekly follow-up once at least 70% of the active plan's activities are completed
  (`completed_count * 100 >= total_activities * 70`, integer-safe, enforced only by the
  backend in `FollowupService._validate_plan_ready`; a direct API call below 70% is rejected
  the same way the UI is gated). `0` total activities is never eligible.
- **AI-varied weekly follow-up questions**: Gemini may only (a) select a 5–8 subset of a
  deterministic KB06 candidate pool (`select_weekly_followup_questions`, prioritized toward
  completed activities) and (b) reword the Arabic text — it can never change which KB06
  template or KB02 activity a question maps to, so scoring is unaffected by wording. The
  generated/selected set is frozen on the weekly-plan database row. Reloads, Render cold
  starts, process restarts, and another worker therefore return the exact same set without
  calling Gemini again; the process-local cache is only an optimization.
- **"افهم أكثر" activity explanations**: a per-activity AI explanation (purpose, 3–5 steps, an
  example dialogue, and a simpler same-activity alternative) built only from that one KB02
  activity's own fields — no child, parent, or session data is ever read to build it.
- **Source-reference UX**: AI cards now show a compact, collapsed-by-default
  "المصادر المعتمدة (N)" disclosure with human-readable labels (resolved server-side from the
  approved KB context, never from provider output) instead of raw comma-separated source IDs;
  the technical ID remains available as small secondary text for traceability.

Both new AI operations reuse the same disabled-by-default / fake-provider-in-E2E / strict-
validation-with-deterministic-fallback pipeline as Milestone 2 — see `docs/RAG_AI_DESIGN.md`
and `docs/API_SPEC.md` for the exact schemas and endpoints.
