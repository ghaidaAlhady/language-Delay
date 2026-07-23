# Project Status and Milestones — Smart Guide for Children's Language Delay

**Audit date:** 2026-07-23
**Branch audited:** `feature/web-frontend` (not merged to `main`; nothing from this branch has been committed or pushed — confirmed via `git status`/`git log`)
**Method:** Direct inspection of repository files, live execution of the existing automated test suites (backend `pytest`, frontend `vitest`, frontend `playwright`), and `git`/database inspection. No application code was written, modified, or deleted to produce this audit. Two files were created: this report and (in a prior, separate session turn) `PROGRESS.md`, which already existed before this audit began.

---

## 1. Executive Summary

| Metric | Estimate | Basis |
|---|---|---|
| Overall project completion | **~80%** | Backend + frontend implementation both feature-complete against the approved scope; testing/hardening and docs are the main gaps |
| Backend completion | **~95%** | 30/30 planned endpoints implemented, 161/161 tests passing, only Google Sign-In and chatbot explicitly deferred (approved deferrals, not gaps) |
| Frontend completion | **~90%** | 24 pages implemented and wired to the real backend; core flow visually and functionally verified live; E2E suite not yet fully green |
| AI / knowledge-base completion | **~90% KB, 0% LLM** | KB01–KB05 fully loaded/validated/traceable; **no Gemini or any LLM is integrated** — reports/plans are generated deterministically from KB04 templates by design (see §2, §6) |
| Testing completion | **~75%** | Backend unit/integration: 100% passing. Frontend unit/component: 100% passing. Frontend E2E: written for all required scenarios but **not yet reliably green** (see §8) |
| Deployment readiness | **~30%** | No CI workflow, no production Dockerfile validation this session, no deployed environment; Dockerfile/docker-compose exist but are backend-only and unverified this session |

**Current stage:** Feature-complete MVP (backend + web frontend) on an unmerged feature branch, in the test-hardening/documentation phase before final sign-off.

**Most important blocker:** The Playwright end-to-end suite is not consistently green. The most recent full run (serial, single worker, zero concurrency) still showed **15 passed / 11 failed / 1 flaky out of 27** cases, with the *same* failures reproducing regardless of parallelism — ruling out the concurrency theory investigated during this session. The underlying **functional flows have been independently verified correct** (see §7 evidence), so this is currently assessed as a test-environment/harness reliability issue (a long-lived, heavily-reused dev SQLite database and possible resource contention from other tools running concurrently on the same machine during the timed run), not a confirmed application defect — but it is **not yet root-caused**, and the weekly follow-up flow in particular has zero confirmed successful E2E completions (`followups` table = 0 rows in the dev DB despite the feature being implemented and unit-tested).

**Next recommended action:** Milestone 1 (Project Stabilization) — reset the dev database, isolate the E2E run from any other concurrent process, and get a clean, reproducible pass/fail baseline for all 27 E2E cases before writing any more code.

*All percentages above are estimates derived from the evidence tables in this report, not precise measurements.*

---

## 2. Current Project Architecture

### As actually implemented (verified)

- **Frontend:** React 19 + TypeScript (strict) + Vite 8 + Tailwind CSS v4 + React Router v7 (data router) + TanStack Query v5 + React Hook Form + Zod + Vitest/Testing Library/MSW + Playwright. Located in `frontend/`, untracked in git as of this audit.
- **Backend:** Python 3.13 + FastAPI + SQLAlchemy 2.x (async, `aiosqlite`) + Alembic + Pydantic v2 + `python-jose` (JWT) + `passlib`/Argon2 + `slowapi` (rate limiting) + `structlog` + ReportLab/`arabic_reshaper`/`python-bidi` (PDF). Located in `backend/`.
- **Database:** SQLite (`backend/language_delay.db` for dev), 6 Alembic migrations in `backend/alembic/versions/`. Tables confirmed present: `users`, `refresh_tokens`, `children`, `assessments`, `assessment_answers`, `assessment_domain_results`, `reports`, `weekly_plans`, `weekly_plan_activities`, `followups`.
- **AI model/provider:** **None integrated.** `LLM_PROVIDER`/`LLM_API_KEY`/`LLM_MODEL` exist only as unused config surface in `backend/app/core/config.py` (`Settings.llm_configured` property, never `True` in this deployment). `backend/app/services/report_service.py` docstring: *"Every sentence in a generated report comes from a KB04 narrative template ... this is the *only* report-generation path."* A repository-wide search for `gemini`/`Gemini`/`GEMINI` in `backend/app` returned **zero matches**.
- **Knowledge-base format:** 5 Excel workbooks (`knowledge_base/KB01.xlsx`–`KB05.xlsx`), loaded via `openpyxl`/`pandas` at process startup (`backend/app/main.py` lifespan handler), validated structurally and semantically (`backend/app/rag/loader.py`, `normalizer.py`), cached in-memory for the process lifetime (`backend/app/repositories/knowledge_base_repository.py`). Never touches the SQL database.
- **Main components:** `backend/app/{api,core,models,rag,repositories,schemas,security,services}`; `frontend/src/{api,app,components,features,layouts,pages,routes,schemas,services,types,utils}`.
- **Data flow:** Browser (Vite dev server, `127.0.0.1:5173`) → `frontend/src/api/client.ts` (typed fetch wrapper, bearer JWT, single-flight refresh-and-retry on 401) → FastAPI (`127.0.0.1:8000`, prefix `/api/v1`) → SQLAlchemy async session → SQLite. KB data is read from the in-memory repository, never the SQL DB.
- **Frontend↔backend communication:** **Real, not mocked**, and independently verified live during this session (see §7). CORS is configured via `CORS_ORIGINS` env var (`backend/.env(.example)`), covered by `backend/tests/test_cors.py` (3/3 passing).

### Documented vs. implemented — differences found

| Document | Says | Actually implemented | Evidence |
|---|---|---|---|
| `PROJECT_SPEC.md` | Frontend is a **Flutter mobile app** | Frontend is a **React web app** | Explicit, repeated user instruction this session directed the web-app pivot; `frontend/` contains a Vite/React project, no Flutter/Dart files exist anywhere in the repo |
| `docs/ARCHITECTURE.md` | — | Document explicitly scopes itself to backend only: *"This document describes the **backend** built this session. The Flutter mobile app is not yet implemented"* | `docs/ARCHITECTURE.md` line 5 — no frontend architecture doc exists yet (`docs/FRONTEND_ARCHITECTURE.md` not found) |
| `docs/PRD.md`, `docs/SRS.md` | Product requirements / software requirements | Still placeholder stub text: *"To be completed by Claude Code..."* | File contents unchanged from repository scaffold |
| `frontend/README.md` | — | Still the default `create-vite` template text (Oxlint/React-Compiler boilerplate), not project-specific | File contents verified unchanged from scaffold |
| Repo overview (`CLAUDE_CODE_PROMPT.md`) | Mentions Google Sign-In, chatbot | Neither implemented | `docs/DECISIONS_AND_ASSUMPTIONS.md` — both explicitly and deliberately deferred, not gaps against this session's approved scope |

---

## 3. Completed Work

| Feature | Status | Evidence | Notes |
|---|---|---|---|
| FastAPI app foundation (config, logging, DB, error envelope, CORS, rate limiting) | Completed | `backend/app/main.py`, `app/core/{config,database,errors,logging,middleware,rate_limit}.py` | — |
| Auth: register/login/refresh/logout/me/delete | Completed | `backend/app/api/v1/auth.py`, `app/services/auth_service.py`; tests `test_auth_api.py`, `test_auth_service.py` | Argon2 + JWT + rotating opaque refresh tokens |
| Child CRUD | Completed | `backend/app/api/v1/children.py`; frontend `pages/{AddChildPage,ChildDetailPage,EditChildPage,ChildrenListPage}.tsx` | Live-verified: real child "سارة" created, Arabic round-trip confirmed |
| KB01–KB05 loading & validation | Completed | `backend/app/rag/{loader,normalizer,builder,schemas,parsing}.py`; tests `test_kb_loader.py`, `test_kb_parsing.py`, `test_kb_repository.py` | Row counts cross-checked against raw `.xlsx` via `openpyxl` earlier in this session (591 records total) |
| Assessment start/questions/answer/complete | Completed | `backend/app/api/v1/assessments.py`; frontend `AssessmentIntroPage.tsx`, `AssessmentTakePage.tsx` | Live-verified: full 20-question flow, real "طبيعي" 100% result rendered |
| Scoring / decision-rule engine | Completed | `backend/app/services/scoring_service.py`; test `test_scoring_service.py` | Weighted 5-point→KB05 yes/no mapping, documented in `DECISIONS_AND_ASSUMPTIONS.md` |
| Deterministic report generation + Arabic PDF | Completed | `backend/app/services/{report_service,pdf_service}.py`; frontend `ReportPage.tsx` | Live-verified: real `REP-0001`/`REP-0002` report text, real downloadable PDF (`PDF document, version 1.3`) |
| Weekly plan generation + completion + alternative activity | Completed | `backend/app/services/weekly_plan_service.py`; frontend `WeeklyPlanPage.tsx` | Live-verified: 14 real KB02 activities across 7 real day names; mark-complete and alternative-activity both exercised successfully in a live run |
| Specialist referral surfacing | Completed | KB03 `الإحالة إلى أخصائي` field threaded through `AssessmentDomainResultResponse`/`ReportResponse`; frontend referral card in `AssessmentResultPage.tsx` | Live-verified for a real "تأخر ملحوظ" case (Case 4, all-No answers) |
| Ownership isolation (404-not-403) | Completed | Every child-scoped repository/service; tests `test_*_ownership_isolation` across `test_children_api.py`, `test_assessments_api.py`, etc. | — |
| Non-diagnostic disclaimer guarantee | Completed | `backend/app/core/constants.py::DISCLAIMER_AR`; test `test_non_diagnostic.py`; frontend E2E `non-diagnostic.spec.ts` (assertion logic written, not yet passing — see §8) | Backend-side guarantee is test-verified; frontend E2E confirmation is not yet green |
| CORS fix for the web frontend | Completed | `backend/.env(.example)` `CORS_ORIGINS`; `backend/tests/test_cors.py` (3/3 passing) | Minimal, pre-approved, documented change; no other backend code touched |
| 24 frontend pages, all wired to real API | Completed | `frontend/src/pages/*.tsx`, `src/routes/router.tsx` | No hardcoded/mock data found in a repo-wide `TODO`/`FIXME`/`placeholder`/`mock data` search of `frontend/src` |
| Centralized typed API client + Arabic error mapping | Completed | `frontend/src/api/client.ts`, `src/utils/errorMessages.ts` | Covers 400/401/403/404/409/422/429/500/503 + network/timeout/offline; unit-tested (11 tests) |
| RTL Arabic UI | Completed | `frontend/index.html` (`dir="rtl" lang="ar"`), Tajawal font | Verified visually (screenshot) and via Playwright assertion in `smoke.spec.ts`/`responsive-rtl.spec.ts` |
| Backend automated tests | Completed | `backend/tests/` | **161/161 passing**, run fresh during this audit |
| Frontend unit/component tests | Completed | `frontend/src/**/*.test.ts(x)` | **101/101 passing**, run fresh during this audit |

---

## 4. Partially Completed Work

| Feature | What Exists | What Is Missing | Evidence | Risk |
|---|---|---|---|---|
| Frontend E2E test suite | 27 Playwright test cases written covering all 10 required scenarios + RTL/responsive/session/offline/error/non-diagnostic coverage; global setup with rate-limit-aware shared login | A clean, reproducible, fully-green run. Most recent run: 15 passed / 11 failed / 1 flaky, identical result set in both parallel and serial mode | `frontend/e2e/*.spec.ts`; live run output captured this session | High — this is the primary remaining unknown before the frontend can be called verified end-to-end |
| Weekly follow-up, frontend-E2E path specifically | Backend fully implemented and unit-tested (`followup_service.py`, `test_followup_service.py`, `test_followups_api.py`); frontend pages built (`ReassessmentPage.tsx`, `FollowupDetailPage.tsx`) | A single confirmed successful run of the full UI flow. `followups` table in the dev DB currently has **0 rows** — no automated or manual run this session has completed it successfully end-to-end via the browser | `SELECT COUNT(*) FROM followups` → `0`; `case-10-followup-reassessment.spec.ts` is in the current failing set | Medium — backend correctness is solid; only the UI path is unconfirmed |
| Frontend documentation | `PROGRESS.md` exists and is current | `frontend/README.md` (still Vite default), `docs/FRONTEND_ARCHITECTURE.md`, `docs/FRONTEND_API_INTEGRATION.md`, `docs/FRONTEND_TEST_PLAN.md`, `docs/FRONTEND_MANUAL_TEST_CASES.md` — none exist | Confirmed absent via `ls docs/ \| grep -i frontend` and file read | Low — doesn't block functionality, blocks handoff/review |
| Frontend refresh-token security | Access token in-memory only, refresh token in `sessionStorage` (not `localStorage`) — a deliberate improvement documented in code | True XSS-hardening needs httpOnly/Secure/SameSite cookies, which requires a backend change not made this session | `frontend/src/services/tokenStore.ts` docstring | Low-Medium — documented, known, acceptable for MVP per session scope |
| CI / automated pipeline | None | No `.github/workflows/` exists for either backend or frontend | Confirmed absent via directory listing | Medium — no automated regression gate before merge |
| Weekly-plan **history** (plural) | Backend keeps old plans soft-deactivated (`is_active` flag) for audit purposes | No API endpoint lists historical (inactive) plans — only the one current active plan is queryable | `docs/DECISIONS_AND_ASSUMPTIONS.md` (documented limitation); frontend `WeeklyPlanPage.tsx` only ever shows the active plan | Low — documented, deliberate MVP scope |

---

## 5. Not Started or Missing Work

| Missing Feature | Why It Is Needed | Dependencies | Suggested Priority |
|---|---|---|---|
| CI workflow (lint/typecheck/test/build gate) | Prevent regressions before merge to `main`; required by `CLAUDE_CODE_PROMPT.md` | None technical; needs a decision on CI provider | Should Have |
| Frontend documentation set (5 files listed in §4) | Handoff, review, and onboarding | None | Must Have (before declaring the frontend session done) |
| Clean E2E baseline | Confidence that the shipped code actually works end-to-end, not just in isolated manual checks | Reset dev DB; isolate test run from other processes | Must Have |
| Google Sign-In | In `PROJECT_SPEC.md`/`CLAUDE_CODE_PROMPT.md`, explicitly deferred both backend sessions | `google-auth` Python package, live OAuth client credentials | Nice to Have (approved deferral) |
| Chatbot | In `CLAUDE_CODE_PROMPT.md`, explicitly deferred, and explicitly **forbidden** in this session's frontend instructions ("Do not add a chatbot") | N/A | Out of scope — do not build |
| Production deployment / hosting | No deployed environment exists | Infra decision (host, domain, secrets management) | Should Have, after Must Haves |
| English localization | `PROJECT_SPEC.md` mentions English support; this session's frontend instructions specify Arabic-only | Would need i18n library + translated content | Out of scope for this session per explicit instruction; flag for a future decision |

---

## 6. Prototype, Mock, and Real Implementation Check

- **Screens that are only visual prototypes:** None found. Every one of the 24 frontend pages makes real API calls via the centralized client (`frontend/src/api/*.ts`); repo-wide search for mock/hardcoded/placeholder patterns in `frontend/src` returned zero matches outside the legitimate `frontend/src/tests/mocks/` directory (which is Vitest/MSW test infrastructure, never imported by application code — verified by import graph).
- **Hardcoded responses:** None found in application code.
- **Mock assessment results:** None. Scoring is entirely backend-computed (`scoring_service.py`); frontend never calculates or invents a result.
- **Mock weekly plans:** None. Plan generation is entirely backend-computed (`weekly_plan_service.py`).
- **Placeholder Gemini/LLM responses:** N/A — no LLM is called at all (by design, see §2). Reports are template-grounded, not "placeholder AI text"; every sentence traces to a real KB04 row.
- **APIs not connected to the frontend:** None found. All 30 backend endpoints have a corresponding call site in `frontend/src/api/*.ts` (cross-checked against `docs/API_SPEC.md`'s endpoint table).
- **Buttons that do not perform real actions:** None found during this audit's code review; live testing this session exercised "mark complete," "request alternative activity," "generate report," "generate weekly plan," "compare with previous assessment," and "download PDF" and observed real state changes each time.
- **Pages without backend integration:** None. The only pages that don't call the backend are the static content pages (`AboutPage`, `HowItWorksPage`, `PrivacyPage`, `DisclaimerPage`), which correctly have no reason to.

---

## 7. End-to-End User Flow Verification

| # | Step | Status | Evidence |
|---|---|---|---|
| 1 | Open the application | Working | Live-verified: landing page screenshot captured, correct RTL/branding/copy |
| 2 | Enter child information | Working | Live-verified: real child created via `AddChildPage`, Arabic name round-tripped |
| 3 | Select/determine child age | Working | Backend computes `age_years`/`is_assessment_age_eligible` from DOB; live-verified for ages 2 (via full run) and boundary cases (age 1, age 6 → correctly hidden/rejected) |
| 4 | Load age-appropriate questions | Working | Live-verified: 20 real KB05 questions loaded and displayed one at a time with progress |
| 5 | Submit Yes/No-equivalent answers | Working | Live-verified: full 20-question submission via `ResponseScale` component, real API calls per question |
| 6 | Analyze answers | Working | Live-verified: real domain scores (100%) returned and displayed |
| 7 | Apply decision rules | Working | Live-verified: real KB03 severity/referral/recommendation text displayed, matches decision-rule bands |
| 8 | Generate screening result | Working | Live-verified: "طبيعي" result with 100% confidence displayed |
| 9 | Generate strengths and needs | Working | Live-verified: real strengths list rendered; correctly empty-state when none apply |
| 10 | Generate weekly goal | Working | Live-verified: real weekly-goal text in the generated report |
| 11 | Generate daily activities | Working | Live-verified: 14 real KB02 activities across 7 real days in `WeeklyPlanPage` |
| 12 | Show specialist recommendation when required | Working | Live-verified for a real "تأخر ملحوظ"/referral case (all-No answers) |
| 13 | Save the result | Working | Backend persists `assessments`, `assessment_domain_results` (22 and 80 rows respectively in the dev DB, confirming real persistence across many runs) |
| 14 | Display the result in the frontend | Working | Live-verified, screenshots captured |
| 15 | Complete weekly follow-up | **Not Verified** | Backend/service layer is unit-tested and code-reviewed as correct, but **zero successful end-to-end completions observed** this session (`followups` table = 0 rows; `case-10` currently fails in the E2E suite) |
| 16 | Update the report and plan (post-follow-up) | **Not Verified** | Depends on step 15 completing; the code path exists (`followup_service.py` auto-regenerates the plan) but has not been observed to execute successfully via the UI |

---

## 8. Test and Quality Review

**Backend (`backend/tests/`, run fresh during this audit):**
```
161 passed, 7 warnings in 50.63s
```
Covers: unit tests (KB loading/parsing/repository, scoring, age service, PDF service), service-level tests (auth, children, assessments, reports, weekly plans, followups), API integration tests (one file per resource), CORS tests, and a dedicated non-diagnostic-guarantee test. No failing backend tests.

**Frontend unit/component (`frontend`, Vitest, run fresh during this audit):**
```
Test Files  20 passed (20)
Tests  101 passed (101)
```
Covers: Zod schema validation, the API client's full request/error/401-refresh-retry matrix, token storage semantics, Arabic error-message mapping (all required HTTP statuses), Arabic date/number formatting, assessment answer-mapping helpers, and component-level behavior (login/register/child-form/child-list/assessment-questions/progress/result-cards/report/weekly-plan/confirm-dialogs/protected-routes) across loading/error/empty/success states. No failing tests.

**Frontend E2E (`frontend/e2e/`, Playwright, 27 test cases across `smoke.spec.ts` + 10 numbered case files + `resilience.spec.ts` + `non-diagnostic.spec.ts` + `responsive-rtl.spec.ts`):**
- Most recent full run (serial, 1 worker, retries=1): **15 passed, 11 failed, 1 flaky**.
- The **same 10 tests fail** whether run with 1 or 2 workers, which rules out a simple concurrency/database-locking explanation investigated during this session.
- Real, confirmed bugs found and fixed during this session's debugging (evidence the process is working, not just guessing):
  1. Backend rate-limiting: E2E tests were each registering a fresh account, hitting `POST /auth/register`'s real 5/minute limit. Fixed by switching to one shared, pre-registered account with per-test login (`e2e/helpers.ts::SHARED_PARENT_EMAIL`, 10/minute limit).
  2. A genuine race condition in the test helper's answer-submission loop (checking `page.url()` synchronously instead of waiting for a definitive UI state) — fixed (`e2e/helpers.ts::waitForTakeStep`).
  3. An error-message edge case: an offline `fetch()` can hang until the client's own 15s timeout instead of rejecting immediately, which surfaced as a "timeout" message instead of "offline" — fixed (`frontend/src/utils/errorMessages.ts`, now covered by an added unit test).
- **Unresolved as of this audit:** even after those three fixes, the same 10-11 tests still fail, and the diagnostic run took an anomalous 2.7 hours (expected: 15-20 minutes), suggesting either (a) resource contention from other tools running concurrently on the same machine during that specific run, and/or (b) accumulated state in the long-lived dev database (77 children, 400 answers, 294 refresh tokens as of this audit) causing slower responses than a clean environment would produce. This has **not been conclusively root-caused**.
- **Whether the project can currently be safely demonstrated:** Yes, for a live, manually-driven walkthrough — every step in §7 marked "Working" has been independently, visually confirmed this session with real backend data. **Not yet safe to claim as "fully automated-test-verified end-to-end"** — that status is blocked on resolving the E2E suite.

**Missing critical tests:** None identified as missing in *scope* — coverage exists for every required case. The gap is *reliability*, not *coverage*.

---

## 9. Milestone Plan

### Milestone 1 — Project Stabilization
- **Objective:** Get a clean, trustworthy, reproducible E2E baseline.
- **Tasks:** Reset/recreate the dev SQLite database from a clean Alembic `upgrade head`; re-run the full Playwright suite in isolation (no other build/test tools running concurrently); capture and diagnose whichever failures remain with full traces; fix root causes (not symptoms).
- **Dependencies:** None.
- **Deliverables:** A documented, reproducible E2E pass rate; root-cause notes for any remaining failures.
- **Acceptance criteria:** All 27 E2E cases pass in at least 2 consecutive clean runs.
- **Estimated difficulty:** Medium.

### Milestone 2 — Weekly Follow-Up Verification
- **Objective:** Get at least one confirmed, observed, successful completion of the full follow-up/reassessment UI flow.
- **Tasks:** Manually walk `case-10`'s flow (or fix it if a real bug is found); confirm a `followups` row is created and the weekly plan regenerates.
- **Dependencies:** Milestone 1 (a stable environment makes this diagnosable).
- **Deliverables:** A passing `case-10` E2E test; a non-zero `followups` row observed in a real run.
- **Acceptance criteria:** `case-10-followup-reassessment.spec.ts` passes; manual walkthrough confirms the updated report/plan render correctly.
- **Estimated difficulty:** Low-Medium (backend is already solid; likely a frontend timing/selector issue at worst).

### Milestone 3 — Frontend Documentation
- **Objective:** Close the documentation gap identified in §4.
- **Tasks:** Write `frontend/README.md` (install/run/env/test commands, folder structure), `docs/FRONTEND_ARCHITECTURE.md`, `docs/FRONTEND_API_INTEGRATION.md`, `docs/FRONTEND_TEST_PLAN.md`, `docs/FRONTEND_MANUAL_TEST_CASES.md`.
- **Dependencies:** None — can run in parallel with Milestone 1/2.
- **Deliverables:** 5 documentation files, accurate to the actual implementation.
- **Acceptance criteria:** A new developer could follow `frontend/README.md` alone to install, run, and test the project locally.
- **Estimated difficulty:** Low.

### Milestone 4 — CI Pipeline
- **Objective:** Automated regression gate before any future merge.
- **Tasks:** Add `.github/workflows/` for backend (`ruff`, `mypy`, `pytest`, Alembic check) and frontend (`typecheck`, `lint`, `vitest`, `build`; E2E optionally as a separate, longer-running job).
- **Dependencies:** Milestone 1 (E2E must be reliable before gating on it).
- **Deliverables:** A working GitHub Actions workflow.
- **Acceptance criteria:** A PR against `main` shows all checks passing.
- **Estimated difficulty:** Low-Medium.

### Milestone 5 — Merge and Release Readiness
- **Objective:** Get `feature/web-frontend` safely mergeable.
- **Tasks:** Final `git status`/secrets scan; squash/organize commit history if desired; open a PR; address review feedback.
- **Dependencies:** Milestones 1-4.
- **Deliverables:** A mergeable, reviewed PR.
- **Acceptance criteria:** Explicit user approval to commit/push (not yet given — nothing has been committed this session per instruction).
- **Estimated difficulty:** Low.

*(Milestones for already-completed backend/frontend feature work are intentionally omitted per the instruction not to include milestones for finished work.)*

---

## 10. Prioritized Remaining Backlog

1. **Reset dev DB and re-run full E2E suite in isolation** — Must Have — Milestone 1 — `backend/language_delay.db`, `frontend/e2e/**` — Depends on: nothing — Done when: a clean baseline pass/fail count is captured — Test: `npx playwright test` (all projects)
2. **Root-cause and fix remaining E2E failures** — Must Have — Milestone 1 — files TBD by diagnosis — Depends on: #1 — Done when: 27/27 E2E cases pass twice in a row — Test: `npx playwright test`
3. **Confirm weekly follow-up flow completes successfully at least once** — Must Have — Milestone 2 — `frontend/e2e/case-10-followup-reassessment.spec.ts`, `frontend/src/pages/{ReassessmentPage,FollowupDetailPage}.tsx` — Depends on: #1 — Done when: `followups` table has ≥1 real row from an automated or manual run — Test: `case-10` E2E + manual walkthrough
4. **Write `frontend/README.md`** — Must Have — Milestone 3 — `frontend/README.md` — Depends on: nothing — Done when: a fresh clone + README alone gets the app running — Test: manual dry-run of the documented commands
5. **Write `docs/FRONTEND_ARCHITECTURE.md`, `FRONTEND_API_INTEGRATION.md`, `FRONTEND_TEST_PLAN.md`, `FRONTEND_MANUAL_TEST_CASES.md`** — Must Have — Milestone 3 — `docs/FRONTEND_*.md` — Depends on: nothing — Done when: all 4 files exist and match the real implementation — Test: manual review against actual code
6. **Add CI workflow** — Should Have — Milestone 4 — `.github/workflows/*.yml` — Depends on: #1, #2 — Done when: a PR shows all checks green — Test: open a throwaway PR
7. **Decide and implement production deployment target** — Should Have — Milestone 5 — infra-specific — Depends on: #1-6 — Done when: app is reachable at a real URL — Test: manual smoke test of the deployed URL
8. **Google Sign-In** — Nice to Have — none (approved deferral) — `backend/app/api/v1/auth.py`, `google-auth` dependency — Depends on: live OAuth credentials (external decision) — Done when: Google login works end-to-end — Test: new API + E2E test
9. **English localization** — Nice to Have — none — i18n library + content — Depends on: explicit scope decision (currently out of scope) — Done when: a language toggle works — Test: new component/E2E tests

---

## 11. Recommended Next Milestone

**Milestone 1 — Project Stabilization** should be started next.

- **Why it should be first:** Every other remaining milestone either depends on it directly (Milestone 2, 4) or benefits from not being built on top of an unverified foundation. Right now, the single biggest open question is *"does the shipped code actually work end-to-end, reliably, or not?"* — and that question is currently unanswered, not merely "answered but not yet documented."
- **Which problems it resolves:** Distinguishes real application bugs (if any exist) from environmental noise in this session's very long-lived, heavily-reused dev database and test machine; gives a trustworthy number to report instead of "15/27, cause unclear."
- **Which files will probably be affected:** Likely none in `backend/app` or `frontend/src` (the underlying features are already independently verified correct via manual live testing) — most likely only `frontend/e2e/**` (test code) and possibly `backend/language_delay.db` (data reset, not schema/code).
- **What must be completed before moving to the following milestone:** A clean, reproducible E2E baseline (ideally 27/27, or a short, understood, justified list of exceptions).
- **What should not be worked on yet:** New features, CI, deployment, or documentation content that describes test *results* (documentation *structure* — Milestone 3 — can proceed in parallel since it doesn't depend on test outcomes).

---

## 12. Commands for Running the Project

All commands verified against the actual repository during this audit.

**Install dependencies:**
```bash
# Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat for cmd, or Activate.ps1 for PowerShell
pip install -r requirements.txt -r requirements-dev.txt

# Frontend
cd frontend
npm install
```

**Run the backend:**
```bash
cd backend
source .venv/Scripts/activate
cp .env.example .env   # then set SECRET_KEY to a real random value
alembic upgrade head
uvicorn app.main:app --reload
# -> http://127.0.0.1:8000 (docs at /docs)
```

**Run the frontend:**
```bash
cd frontend
cp .env.example .env   # VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev
# -> http://127.0.0.1:5173
```

**Run tests:**
```bash
# Backend
cd backend && source .venv/Scripts/activate && python -m pytest -q

# Frontend unit/component
cd frontend && npm run test

# Frontend E2E (requires both servers running)
cd frontend && npx playwright test
```

**Run the complete system locally:** Start the backend and frontend commands above in two separate terminals, then open `http://127.0.0.1:5173`.

---

## 13. Final Checklist

### Ready
- FastAPI backend: all 30 endpoints implemented, 161/161 tests passing.
- Frontend: all 24 pages implemented, wired to the real backend, 101/101 unit/component tests passing.
- Core user flow (registration through weekly plan + activity actions): manually live-verified with real data and screenshots this session.
- CORS integration between the Vite dev server and the FastAPI backend: fixed and tested.
- Knowledge-base loading/validation/traceability: complete and tested.
- Non-diagnostic disclaimer guarantee: backend-tested.
- No mock data, hardcoded results, or disconnected buttons found anywhere in `frontend/src` application code.

### Remaining
- A clean, reproducible, fully-green Playwright E2E run.
- Confirmed successful completion of the weekly follow-up flow (currently 0 observed successes).
- Frontend documentation set (`README.md` + 4 `docs/FRONTEND_*.md` files).
- CI workflow.
- Production deployment.

### Blocked or Unclear
- **Root cause of the E2E suite's ~40% failure rate:** not yet conclusively diagnosed; needs a clean-environment isolated run (Milestone 1) before further code changes are justified.
- **Whether to pursue Google Sign-In / English localization:** both are explicitly out of this session's approved scope; require an explicit product decision before any implementation.
- **Deployment target:** no infrastructure decision has been made (hosting provider, domain, secrets management strategy).
