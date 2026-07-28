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

## Current Agent Handoff

### Authoritative focused-corrections handoff (2026-07-26)

- **Repository path:** `C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub`
- **Current branch:** `feature/web-frontend`; no branch change was made.
- **Latest commit:** `638b324ccd9b52ee424d1d584bd4c1580b96c134`
  (`fix(followup): verify weekly follow-up persistence and plan linkage`).
- **Working tree:** intentionally not clean. It contains the preserved, uncommitted
  Checkpoint 4 files plus this focused correction checkpoint. No file was staged, committed,
  pushed, reset, cleaned, reverted, or discarded. The local files `AGENTS.md`,
  `agent_test.txt`, and `.claude/settings.local.json` remain preserved.
- **Current milestone:** Milestone 1 — Project Stabilization.
- **Current checkpoint:** Focused corrections after Checkpoint 4; implementation and required
  verification are complete locally and awaiting explicit review.
- **Last completed checkpoint in Git:** Checkpoint 3 at `638b324`.

#### Defects confirmed and exact fixes

- User-facing report/result timing could expose KB03 intervals of several weeks or months.
  Reports now normalize the timing to `إعادة التقييم بعد أسبوع وتحديث الخطة`, and the result
  and report pages consistently label it as weekly follow-up. Initial assessment scoring,
  support level, referral, and KB01–KB05 content were not changed.
- ReportLab used a font path that was not portable and could fall back to a non-Arabic font.
  The backend now packages the redistributable SIL-OFL Tajawal font, shapes Arabic with
  `arabic_reshaper`, applies bidirectional layout with `python-bidi`, wraps logical Arabic
  words, and embeds the TrueType font in every Arabic PDF. A configured font remains an
  optional override; an invalid override safely falls back to the packaged font.
- The parent-facing assessment result displayed an unexplained confidence value. That
  display was removed while preserving the backend field/calculation and all clinical rules.
- Weekly activity controls used an unclear label and could dispatch two requests during a
  rapid double click. They now display `تم` before completion and `مكتمل` after completion;
  a synchronous in-flight guard prevents duplicate same-slot requests, while the persisted
  backend state still supports reload and intentional un-completion.
- A completed active plan had no clear follow-up action. The plan page now shows the approved
  completion panel and routes to the exact child/plan only when all activities in the current
  active plan are complete. It never creates a follow-up before answers are submitted and
  disappears when the replacement plan becomes active.
- Weekly follow-up reused the initial KB05 assessment. A distinct deterministic KB06 source
  now supplies 5–8 observable, parent-friendly questions bound to the active plan's age,
  domain, goal/skill metadata, and real KB02 activities. Specific activity/domain matches
  are preferred; a same-domain generic template is used only when no specific match exists.
  KB05 is not a follow-up fallback.

#### KB06, persistence, ownership, and replacement-plan design

- `knowledge_base/KB06.json` contains ten structured records: two specific templates for
  each of the four language domains plus two generic domain-preserving fallbacks. Records
  include age bounds, domain, goal/skill keys, applicable approved activity IDs, Arabic
  question text, response type, required flag, deterministic weight, active flag, and a
  non-diagnostic source note.
- The KB loader, normalizer, typed schemas, builder, and repository load KB06 once and select
  questions deterministically. Selection follows the stored plan activity order and returns
  up to eight questions, with a minimum of five.
- New plan-scoped endpoints are:
  `GET /api/v1/weekly-plans/{plan_id}/followup-questions` and
  `POST /api/v1/weekly-plans/{plan_id}/followup`. The legacy assessment-scoped creation
  route no longer starts a KB05 follow-up.
- Migration `5f31d8aee912_link_followups_to_weekly_plans.py` adds a unique weekly-plan link
  plus persisted answers/question context while retaining compatibility with legacy rows.
- The service verifies parent ownership, the exact current active plan, full plan completion,
  the complete expected question set, and bounded response values. Ownership mismatches are
  masked as 404; stale/inactive plan attempts are rejected.
- Submission is idempotent per weekly plan at both service and database levels. The existing
  record is returned on retries. A successful first submission stores its exact context and
  answers, computes deterministic weekly-plan progress, deactivates the old plan, and creates
  the next plan through the existing approved weekly-plan service without creating a fake
  second initial assessment.

#### Test commands and exact results

Backend:

- Focused follow-up service tests — **7 passed**.
- Focused follow-up API tests — **6 passed**.
- Focused report/PDF groups — **12 passed**.
- `.\.venv\Scripts\python.exe -m pytest -q` — **167 passed, 7 warnings in 51.84s**.
- `.\.venv\Scripts\python.exe -m mypy app` — **passed; 67 source files checked**.
- Ruff on every changed backend application/test file and the new migration — **passed**.
- `ruff check .` — **not clean because of 37 pre-existing errors confined to old
  `alembic/env.py` and old migration files**; no unrelated legacy lint was rewritten.
- A disposable empty SQLite database upgraded through every migration to
  `5f31d8aee912 (head)` successfully. Development and E2E databases were not migrated.

Frontend:

- Focused result/report/weekly-plan/reassessment tests — **13 passed**.
- `npm.cmd run test -- --reporter=dot` — **109/109 passed in 22 files**.
- `npm.cmd run typecheck` — **passed**.
- `npx tsc --noEmit -p tsconfig.e2e.json` — **passed**.
- `npm.cmd run lint` — **passed** with the pre-existing warning
  `src/tests/test-utils.tsx:58 react(only-export-components)`.
- `npm.cmd run build` — **passed** with Vite 8.1.5 (224 modules transformed).

Desktop/Chromium E2E:

- Focused Case 10 weekly follow-up flow — **1 passed**.
- Focused Case 2 plus non-diagnostic/PDF flow — **3 passed**.
- Stable focused total — **4/4 passed**.
- Full Desktop/Chromium project, one worker and no retries — **27/27 passed in 5.4 minutes**.
  This run included offline resilience, the complete plan-linked KB06 follow-up/replacement
  flow, reload persistence, and a real UI PDF download with an embedded TrueType font.

#### PDF verification and remaining issues

- The packaged `Tajawal-Regular.ttf` includes Arabic cmap code points and is embedded as
  `/FontFile2`; tests verify shaping produces Arabic presentation forms, no replacement
  character is emitted, and the PDF retains its header and report ID.
- No PDF rasterizer/OCR tool is installed in this environment, so pixel-level visual OCR is
  not automated. Font coverage, shaping/bidi transformation, embedding, parsed structure,
  and the real UI download are the reliable automated layers used here.
- Full backend and frontend tests have no failing assertions. Full frontend lint has one
  pre-existing warning. Repository-wide backend Ruff still reports the 37 legacy Alembic
  errors described above.
- Backend logs still report the pre-existing KB01/KB05 linked-milestone mismatch for some
  age-four questions. It does not affect scoring, referral, follow-up selection, or test
  success, and KB01–KB05 were intentionally preserved.
- The formal Milestone 1 two-consecutive-clean-full-E2E acceptance gate has not yet been
  completed: this checkpoint ran the requested full Desktop project once after focused
  stability and it passed 27/27.

#### Modified and untracked files

Focused-correction tracked modifications:

- `backend/app/api/v1/followups.py`
- `backend/app/core/config.py`
- `backend/app/core/constants.py`
- `backend/app/models/followup.py`
- `backend/app/rag/builder.py`
- `backend/app/rag/loader.py`
- `backend/app/rag/normalizer.py`
- `backend/app/rag/schemas.py`
- `backend/app/repositories/followup_repository.py`
- `backend/app/repositories/knowledge_base_repository.py`
- `backend/app/schemas/followup.py`
- `backend/app/services/followup_service.py`
- `backend/app/services/pdf_service.py`
- `backend/app/services/report_service.py`
- `backend/tests/test_followup_service.py`
- `backend/tests/test_followups_api.py`
- `backend/tests/test_pdf_service.py`
- `backend/tests/test_report_service.py`
- `backend/tests/test_reports_api.py`
- `frontend/e2e/case-02-age-two-all-yes.spec.ts`
- `frontend/e2e/case-10-followup-reassessment.spec.ts`
- `frontend/e2e/non-diagnostic.spec.ts`
- `frontend/src/api/followups.ts`
- `frontend/src/api/queryKeys.ts`
- `frontend/src/features/followup/useFollowups.ts`
- `frontend/src/features/weeklyPlan/WeeklyActivityCard.tsx`
- `frontend/src/pages/AssessmentResultPage.test.tsx`
- `frontend/src/pages/AssessmentResultPage.tsx`
- `frontend/src/pages/FollowupDetailPage.tsx`
- `frontend/src/pages/ReassessmentPage.test.tsx`
- `frontend/src/pages/ReassessmentPage.tsx`
- `frontend/src/pages/ReportPage.test.tsx`
- `frontend/src/pages/ReportPage.tsx`
- `frontend/src/pages/WeeklyPlanPage.test.tsx`
- `frontend/src/pages/WeeklyPlanPage.tsx`
- `frontend/src/tests/fixtures.ts`
- `frontend/src/tests/mocks/handlers.ts`
- `frontend/src/types/api.ts`
- `README.md`
- `docs/API_SPEC.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/DECISIONS_AND_ASSUMPTIONS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/RAG_AI_DESIGN.md`
- `docs/TEST_PLAN.md`
- `PROGRESS.md`

Focused-correction untracked files:

- `backend/alembic/versions/5f31d8aee912_link_followups_to_weekly_plans.py`
- `backend/assets/fonts/OFL.txt`
- `backend/assets/fonts/Tajawal-Regular.ttf`
- `knowledge_base/KB06.json`

Preserved pre-existing Checkpoint 4 modifications/untracked files:

- `PROJECT_STATUS_AND_MILESTONES.md`
- `frontend/src/features/children/useChildren.ts`
- `frontend/src/features/children/useChildren.test.tsx`
- `MANUAL_FRONTEND_TESTING_GUIDE.md`
- `MILESTONE_1_STABILIZATION_REPORT.md`
- `MILESTONE_2_GEMINI_PROPOSAL.md`

Preserved local files outside this correction checkpoint:

- `AGENTS.md`
- `agent_test.txt`
- `.claude/settings.local.json` (ignored)

#### Exact next action and milestone readiness

The exact next action is an explicit human review of the focused correction diff and the
combined pre-existing documentation changes. If approved, stage and commit the correction
files deliberately (use hunk staging for `README.md`/`PROGRESS.md` if the earlier Checkpoint 4
documentation must remain a separate commit). Then run one more clean full Desktop/Chromium
pass in a fresh isolated E2E database to satisfy the existing two-consecutive-run Milestone 1
gate.

All focused correction acceptance criteria are met, but **do not begin the separate
Agent/Gemini architecture milestone yet**. It becomes safe only after explicit review,
intentional commits that leave a controlled tree, and completion/waiver of the remaining
Milestone 1 consecutive-run gate. No Gemini package, key, agent, model call, or deployment was
added in this checkpoint.

#### Safety warnings

- Do not stage or commit `.claude/settings.local.json`, `agent_test.txt`, `.env` files,
  secrets, API keys, databases, `node_modules`, build output, generated reports, logs,
  screenshots, traces, videos, Playwright artifacts, or temporary files.
- Do not mix the preserved Checkpoint 4 offline-resilience change with the focused correction
  commit unless that combined scope is explicitly approved.
- Preserve assessment scoring, specialist-referral rules, and KB01–KB05 content.
- Suggested commit message after explicit review:
  `fix(followup): add plan-linked weekly progress flow`

#### Suggested prompt for the next coding agent

> Review the completed focused corrections on branch `feature/web-frontend` at base commit
> `638b324`. Read `AGENTS.md`, `CLAUDE.md`, `PROJECT_SPEC.md`, `CLAUDE_CODE_PROMPT.md`,
> `PROGRESS.md`, and `PROJECT_STATUS_AND_MILESTONES.md`. Do not discard or mix the preserved
> Checkpoint 4 work. Verify the plan-linked KB06 follow-up, weekly wording, parent-facing
> confidence removal, completion CTA, and embedded Tajawal Arabic PDF. Do not change
> assessment scoring, referral rules, or KB01–KB05. Do not add Gemini or an AI agent. After
> explicit approval, stage only reviewed files, keep local settings/artifacts excluded, and
> run one more fresh no-retry full Desktop/Chromium pass to close the Milestone 1 gate.

### Historical Checkpoint 4 handoff (2026-07-26)

- **Repository path:** `C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub`
- **Current branch:** `feature/web-frontend`; no branch change was made.
- **Latest commit:** `638b324ccd9b52ee424d1d584bd4c1580b96c134`
  (`fix(followup): verify weekly follow-up persistence and plan linkage`).
- **Working tree:** intentionally not clean because Checkpoint 4 is uncommitted. The
  pre-existing/requested untracked `AGENTS.md` and `agent_test.txt` are preserved.
  `.claude/settings.local.json` is present and ignored/preserved.
- **Current milestone:** Milestone 1 — Project Stabilization; formal acceptance is pending
  the two-consecutive-clean-run E2E gate.
- **Current checkpoint:** Checkpoint 4 — Final Regression, Documentation, and Manual
  Testing Readiness; work is complete locally and awaiting review.
- **Last completed checkpoint in Git:** Checkpoint 3 at `638b324`.

#### Work completed

- Re-ran backend and frontend regression checks, type-check, lint, and production build.
- Re-ran the critical registration/login, child, assessment, result, weekly-plan,
  follow-up, replacement-plan, and reload-persistence Desktop/Chromium flows.
- Reproduced the offline failure independently. TanStack Query paused the create-child
  mutation while offline, so the API client never returned the existing Arabic offline
  error. Added `networkMode: "always"` only to `useCreateChild` and a hook regression test.
- Verified the focused offline E2E passes after the fix.
- Ran the complete desktop project once and reran its sole failure individually.
- Verified port/database isolation and that `backend/language_delay.db` remained at
  `520192` bytes with UTC modification time `2026-07-23 19:55:48`.
- Stopped Checkpoint 4 test servers and removed the task-local bytecode cache, pytest temp
  tree, Playwright `test-results`, and disposable E2E database.
- Created the Milestone 1 report, manual testing guide, and Milestone 2 proposal; updated
  project status and local-run documentation.

#### Final test commands and exact results

Backend:

- `.\.venv\Scripts\python.exe -m pytest --collect-only -q` with a task-local
  `PYTHONPYCACHEPREFIX` — **168 tests collected**.
- Every collected backend test was executed in bounded file/logical groups with
  `.\.venv\Scripts\python.exe -m pytest <files-or-node-ids> -q -s` — **168/168 passed**.
  The groups totaled: age 15, auth service 9, auth API 11, child service 8, children API
  8, CORS 3, health 2, assessment service 9, assessments API 11, KB/scoring/traceability/
  non-diagnostic/PDF 51, follow-up/report/weekly-plan services 19, follow-up API 8,
  knowledge-base API 5, reports API 4, and weekly-plans API 5.
- A normal full-process run first failed while importing pandas with
  `ValueError: bad marshal data (unknown type code)`. Fresh bytecode fixed import, but
  several monolithic full-process attempts then hung in this Windows session. No test
  assertion failed; exact bounded groups were used to complete and account for all 168.

Frontend after the code change:

- `npm.cmd run test -- --reporter=dot` — **107/107 passed in 22 files**.
- `npm.cmd run typecheck` — **passed**.
- `npm.cmd run lint` — **passed** with the pre-existing warning
  `src/tests/test-utils.tsx:58 react(only-export-components)`.
- `npm.cmd run build` — **passed**.

Desktop/Chromium E2E, all with `PW_EXTERNAL_SERVERS=1`, isolated port 8001 database,
one worker, and `--retries=0`:

- Critical Case 1 registration/login — **passed** on individual rerun.
- Critical Case 2 child creation/initial assessment/result — **passed**.
- Critical Case 10 weekly plan/follow-up/progress/replacement plan/reload — **passed** on
  individual rerun.
- `resilience.spec.ts --grep "offline network condition"` — **1/1 passed** after the fix.
- Full `node .\node_modules\@playwright\test\cli.js test
  --project=desktop-chromium --retries=0 --reporter=line` —
  **26 passed / 1 failed out of 27 in 4.6 minutes**.
- Sole failed node, Case 9 unanswered-question protection — **passed 1/1** immediately when
  rerun alone. The failure occurred during login: the browser showed a connection error
  while the backend recorded HTTP 200.
- A second complete run was intentionally not started because the first run and Windows
  environment were not stable enough to produce a trustworthy consecutive result.

#### Known remaining issues

- Milestone 1's 27/27-twice gate is still unmet even though no focused functional test
  remains failing.
- The E2E session showed delayed Playwright server startup, one client `EADDRINUSE`, and a
  large port-8001 TIME_WAIT backlog. This is classified as Windows/process/socket
  environment flakiness.
- Real login/register rate limits remain intentionally enabled and can still make heavy
  repeated E2E load flaky. No final failure returned HTTP 429 and no security was weakened.
- The backend virtual environment has corrupted pandas bytecode and should be recreated in
  a separately approved maintenance step.
- Frontend tests still print pre-existing non-failing React `act(...)` and unmatched-route
  diagnostics.

#### Current Checkpoint 4 files

Tracked modifications:

- `PROGRESS.md` — this authoritative handoff.
- `PROJECT_STATUS_AND_MILESTONES.md` — current checkpoint/milestone and verified results.
- `README.md` — accurate React/FastAPI Windows run and safety instructions.
- `frontend/src/features/children/useChildren.ts` — narrow offline mutation behavior.

New Checkpoint 4 files:

- `MILESTONE_1_STABILIZATION_REPORT.md` — final regression and acceptance report.
- `MANUAL_FRONTEND_TESTING_GUIDE.md` — local Windows manual flow.
- `MILESTONE_2_GEMINI_PROPOSAL.md` — documentation proposal only.
- `frontend/src/features/children/useChildren.test.tsx` — offline mutation regression test.

Preserved local files that are not part of Checkpoint 4:

- `AGENTS.md`
- `agent_test.txt`
- `.claude/settings.local.json` (ignored)

#### Manual readiness, remaining work, and exact next action

Manual frontend testing can begin using backend port 8000, the normal development
database, and `MANUAL_FRONTEND_TESTING_GUIDE.md`. Do not use the E2E launcher, port 8001,
or the disposable E2E database for manual testing.

The exact next action is to review this Checkpoint 4 change set. Then, in a fresh Windows
session with a healthy recreated Python virtual environment, run the complete
Desktop/Chromium E2E project twice consecutively from fresh isolated E2E databases with
retries disabled. If both runs pass 27/27, update the milestone documents to mark
Milestone 1 accepted. Do not start Milestone 2 implementation automatically.

#### Safety warnings

- Do not commit, push, merge, reset, clean, revert, deploy, stage, or change branches
  automatically.
- Do not stage `AGENTS.md`, `agent_test.txt`, `.claude/settings.local.json`, `.env` files,
  secrets, API keys, databases, `node_modules`, build output, logs, screenshots, traces,
  videos, Playwright artifacts, or temporary files.
- Assessment scoring, specialist-referral rules, and KB01–KB05 were preserved.
- Suggested commit message after explicit review:
  `fix(frontend): surface offline child submission errors`

#### Suggested prompt for Claude Code or Codex

> Continue Milestone 1 Checkpoint 4 verification only. Read `AGENTS.md`, `CLAUDE.md`,
> `PROJECT_SPEC.md`, `CLAUDE_CODE_PROMPT.md`, `PROGRESS.md`,
> `PROJECT_STATUS_AND_MILESTONES.md`, and `MILESTONE_1_STABILIZATION_REPORT.md`. Confirm
> repository root, branch `feature/web-frontend`, Git status, and recent log without
> changing Git state. Preserve all existing work and local files. In a fresh Windows
> session with a healthy Python virtual environment, verify ports 4173/8001 are free and
> run the complete Desktop/Chromium E2E project twice consecutively from fresh isolated
> databases with retries disabled. Do not use or reset the development database, weaken
> authentication/rate limits, change scoring/referral/KB content, or start Milestone 2.
> Update the reports with exact results, stop test processes, remove generated artifacts,
> and do not commit, push, merge, or deploy.

### Historical Checkpoint 3 completion update (2026-07-26)

- **Repository path:** `C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub`
- **Current branch:** `feature/web-frontend` (confirmed; no branch change was made).
- **Working-tree status:** Not clean by design. Checkpoint 3 has modified tracked files and
  two new untracked implementation/test files. The pre-existing untracked
  `.claude/settings.local.json` and `AGENTS.md` were preserved. The requested
  `agent_test.txt` exists with exactly `Agent is working` and remains untracked.
- **Last commit hash:** `53c6343ce0688180df7ad92524810fbed98fed7d`
  (`docs: add current agent handoff for milestone 1`). The last application-code commit
  remains `bde709beaaae375800641e2a38abdb20c2569f23`.
- **Current milestone:** Milestone 1 â€” Project Stabilization.
- **Current checkpoint:** Checkpoint 3 â€” Weekly Follow-Up E2E Verification,
  **completed locally and not committed**.
- **Last completed checkpoint:** Checkpoint 3. Work stopped before Checkpoint 4.

#### Original weekly follow-up behavior

- Case 10 did create a genuine backend `followups` row and regenerate the weekly plan; it
  was not merely a second assessment.
- However, the test entered the child by direct URL and only checked visible headings. It
  did not prove normal navigation, child/assessment/plan identity, persisted list state,
  duplicate-submit behavior, replacement-plan identity, or reload persistence.
- The follow-up start page did not show the child or active-plan context and did not block
  a follow-up with no active plan or with a plan tied to the wrong assessment.
- The backend accepted follow-up creation without an active plan and could use an active
  plan that did not belong to the previous assessment being followed up.
- The final follow-up action relied only on React mutation pending state, leaving a
  same-render rapid-double-click window.

#### Confirmed defects and exact fixes

1. `FollowupService.complete_followup()` now requires an active weekly plan for the same
   child and verifies that the plan belongs to the previous completed assessment. Existing
   follow-ups are returned idempotently before these precondition checks.
2. `ReassessmentPage` now loads and displays the child and active-plan context, including
   plan date and adherence. It blocks with actionable Arabic UI when no plan exists or the
   active plan is not tied to the latest completed assessment.
3. Child/result UI wording now describes a weekly follow-up instead of a generic
   reassessment/comparison.
4. `AssessmentResultPage` now uses a synchronous in-flight ref around follow-up creation,
   closing the same-tick duplicate-click race while preserving the mutation loading state.
5. Case 10 now follows normal UI navigation and verifies real response IDs, one POST under
   rapid double click, one persisted follow-up row, progress detail after reload, a new
   active plan tied to the second assessment, and plan persistence after reload.
6. Backend service/API tests now cover missing plans, current-assessment plans, cross-child
   plan isolation, unauthenticated access, cross-parent ownership, and idempotent follow-up
   plus plan replacement.
7. E2E setup now seeds the shared parent with a real API request instead of launching an
   extra browser and login. The isolated backend migration/startup is kept in one Python
   launcher; Vite starts directly on E2E-only port 4173 with explicit CORS. An opt-in
   `PW_EXTERNAL_SERVERS` mode lets the Windows test runner own and stop exact processes.
   Production authentication and rate limiting were not weakened.

#### Exact verification results

- Focused desktop Case 10, clean isolated database each time, retries disabled:
  **5/5 successful runs** â€” `1 passed` in 59.3s, 1.0m, 1.2m, 57.6s, and 41.5s.
  Command executed through the bounded external-server wrapper:
  `node .\node_modules\@playwright\test\cli.js test
  e2e/case-10-followup-reassessment.spec.ts --project=desktop-chromium
  --retries=0 --reporter=line` with `PW_EXTERNAL_SERVERS=1`.
- Authentication protection:
  `tests/test_followups_api.py::test_followup_requires_authentication` â€”
  **1 passed**. Unauthenticated follow-up submit, detail, and list all return 401.
- Ownership isolation: focused follow-up/weekly-plan API and service tests â€”
  **4 passed**. Parent B cannot view/submit Parent A's follow-up, view Parent A's plan,
  mark its activity, request an alternative, or generate a plan from Parent A's assessment.
- Validation: focused follow-up and assessment API tests â€” **7 passed**; focused
  `ReassessmentPage` tests â€” **3 passed**. Coverage includes incomplete assessment,
  missing answers, invalid answer value (422), no previous assessment, no prior active
  plan, plan tied to the current rather than previous assessment, and another child's plan.
- Duplicate submission: focused backend service/API tests â€” **2 passed**; focused
  `AssessmentResultPage` tests â€” **3 passed**. A repeated backend request returns the
  existing follow-up, the child retains one row, the replacement plan ID is unchanged,
  and a rapid UI double click sends one POST.
- Assessment-to-follow-up subset: assessment/scoring/follow-up/weekly-plan backend files â€”
  **55 passed**; relevant frontend page files â€” **17 passed**.
- Complete backend suite:
  `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
  --basetemp=<workspace-temp>` â€” **168 passed, 7 warnings in 66.11s**.
- Complete frontend suite:
  `npm.cmd run test -- --reporter=dot` â€” **106 passed in 21 files**.
  The pre-existing React `act(...)` and unmatched test-route warnings remain non-failing.
- Frontend typecheck: `npm.cmd run typecheck` â€” **passed**.
- Frontend lint: `npm.cmd run lint` â€” **passed** with the pre-existing
  `react(only-export-components)` warning in `src/tests/test-utils.tsx:58`.
- Focused backend Ruff check for all changed Python files â€” **passed**.
- Prettier check for all changed frontend files â€” **passed**.
- Complete Desktop/Chromium project, run once with retries disabled:
  **26 passed / 1 failed out of 27 in 4.8m**. Case 10 passed. The sole failure was the
  pre-existing offline-resilience case because no Arabic offline alert appeared within
  20 seconds. No auth rate-limit case failed in this run.

#### Persistence, plan, scoring, referral, and knowledge-base conclusions

- The real follow-up response linked the correct child, previous assessment, and current
  assessment; exactly one row was returned by the authenticated list API.
- Follow-up detail and the replacement weekly plan remained available after full reloads.
- The replacement plan had a new ID, was tied to the second assessment, and remained the
  active plan after reload.
- Assessment scoring and specialist-referral implementation files were not changed, and the
  assessment/scoring subset plus complete backend suite passed.
- No file under `knowledge_base/` was changed. Weekly-plan tests continue to verify that
  generated activity IDs resolve from the approved KB02 activity source.

#### Known failures and remaining risks

- `frontend/e2e/resilience.spec.ts` still fails its pre-existing offline-alert test. This
  was explicitly out of the main Checkpoint 3 scope and did not block weekly follow-up.
- Real login/register rate limits can still make heavy repeated E2E loads flaky, although
  neither the five focused successes nor the one complete desktop run failed on auth.
- Playwright-owned web-server startup/teardown was unreliable in this Windows tool
  environment during diagnosis, and repeated health polling temporarily accumulated
  `TIME_WAIT` sockets on port 5173. The successful verification used E2E port 4173 and
  exact externally owned processes through `PW_EXTERNAL_SERVERS=1`.
- Milestone 1's repository-level acceptance criterion of 27/27 E2E cases in two consecutive
  clean runs is still unmet because the separate offline case remains failing.
- The ignored disposable `backend/language_delay_e2e.db` was regenerated by E2E tests.
  The pre-existing ignored `frontend/playwright-report/` remains. Neither may be staged.

#### Modified and untracked files

Checkpoint 3 modified tracked files:

- `backend/app/services/followup_service.py`
- `backend/run_e2e_server.sh`
- `backend/tests/test_followup_service.py`
- `backend/tests/test_followups_api.py`
- `frontend/e2e/case-10-followup-reassessment.spec.ts`
- `frontend/e2e/global-setup.ts`
- `frontend/playwright.config.ts`
- `frontend/src/pages/AssessmentResultPage.test.tsx`
- `frontend/src/pages/AssessmentResultPage.tsx`
- `frontend/src/pages/ChildDetailPage.tsx`
- `frontend/src/pages/ReassessmentPage.tsx`
- `frontend/src/tests/fixtures.ts`
- `PROGRESS.md`

Checkpoint 3 new untracked files:

- `backend/run_e2e_server.py`
- `frontend/src/pages/ReassessmentPage.test.tsx`

Pre-existing/requested untracked files preserved and excluded from Checkpoint 3:

- `.claude/settings.local.json`
- `AGENTS.md`
- `agent_test.txt`

#### Work still remaining and exact next action

Checkpoint 3 itself requires no further weekly-follow-up work. The exact next action is for
the user to review this diff and test record. If accepted, the user may stage only the
Checkpoint 3 paths listed above and create the suggested commit. Do not begin Checkpoint 4
until the user explicitly approves its scope. The recommended next stabilization task is a
separate focused diagnosis of the offline-resilience alert and standard Windows Playwright
server lifecycle, followed by the milestone-wide 27/27 twice acceptance run.

It is **not yet safe to begin Checkpoint 4 automatically**: explicit approval is required,
and Milestone 1's full 27/27-twice gate remains open. It is technically safe to request that
approval because the Checkpoint 3 weekly-follow-up acceptance criteria are met.

#### Safety warnings and staging boundary

- Never commit, push, merge, reset, clean, revert, deploy, or change branches automatically.
- Safe to stage only after explicit user review: the 15 Checkpoint 3 modified/new
  application, test, runner, and documentation paths listed above.
- Do not stage `.claude/settings.local.json`, `AGENTS.md`, `agent_test.txt`,
  `backend/language_delay_e2e.db`, `frontend/playwright-report/`, `.env` files, databases,
  secrets, `node_modules`, build output, logs, screenshots, traces, videos, or temporary
  artifacts.
- Preserve assessment scoring, specialist-referral rules, and knowledge-base content.
- Suggested Conventional Commit message:
  `fix(followup): verify weekly follow-up persistence and plan linkage`

#### Suggested continuation prompt for Claude Code or Codex

> Read `CLAUDE.md`, `AGENTS.md`, `PROGRESS.md`, `PROJECT_STATUS_AND_MILESTONES.md`,
> `PROJECT_SPEC.md`, and `CLAUDE_CODE_PROMPT.md`. Confirm the repository root, branch
> `feature/web-frontend`, `git status --short`, and recent log without changing Git state.
> Review the authoritative Checkpoint 3 completion update and preserve every existing
> modified/untracked file. Checkpoint 3 is complete locally; do not redo it or start
> Checkpoint 4 without explicit user approval. If Checkpoint 4 is approved as the next
> stabilization task, focus separately on the known offline-resilience alert and standard
> Windows Playwright server lifecycle. Do not weaken auth/rate limiting, scoring,
> specialist-referral rules, or knowledge-base content. Run focused tests after every
> change, update `PROGRESS.md`, report all files, and do not commit/push/merge/deploy.

### Superseded pre-Checkpoint 3 snapshot (retained for history)

- **Repository path:** `C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub`
- **Current branch:** `feature/web-frontend` (confirmed; no branch change was made)
- **Working-tree status before this handoff update:** Not clean. Pre-existing untracked
  files were `.claude/settings.local.json` and `AGENTS.md`. No tracked file was modified.
- **Working-tree status after this handoff update:** Not clean. `PROGRESS.md` is modified;
  `.claude/settings.local.json` and `AGENTS.md` remain untracked and preserved.
- **Last commit hash:** `bde709beaaae375800641e2a38abdb20c2569f23`
  (`fix(assessment): close last-question duplicate-submission race`)
- **Current milestone:** Milestone 1 — Project Stabilization.
- **Current checkpoint:** Checkpoint 3 — not started. No Checkpoint 3 application-code
  commit, tracked working-tree change, or checkpoint report exists.
- **Last completed checkpoint:** Checkpoint 2.1.

### Work already completed

- **Checkpoint 1:** Commit `bade48e` isolated E2E from the development database and added
  deterministic startup. Files: `.gitignore`, `backend/run_e2e_server.sh`, and
  `frontend/playwright.config.ts`.
- **Checkpoint 2:** Commit `5c5d8f6` stabilized child-ID extraction, assessment-flow waits,
  serial authentication-sensitive execution, and the UI busy state. Files:
  `frontend/e2e/helpers.ts`, `frontend/playwright.config.ts`, and
  `frontend/src/pages/AssessmentTakePage.tsx`.
- **Checkpoint 2.1:** Commit `bde709b` added a synchronous submission-in-flight guard,
  a rapid-double-click regression test, and a safer result-navigation race in the E2E helper.
  Files: `frontend/e2e/helpers.ts`, `frontend/src/pages/AssessmentTakePage.tsx`, and
  `frontend/src/pages/AssessmentTakePage.test.tsx`.
- Git history and the regression test support the reported resolution of the final-question
  duplicate-submission race.

### Verified test results

- Backend, rerun 2026-07-26:
  `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=<workspace-temp>`
  — **161 passed, 7 warnings**. The workspace temp directory was removed afterward.
- Frontend unit/component, rerun 2026-07-26:
  `npm.cmd run test -- --reporter=dot` — **102 passed in 20 files**. Vitest emitted
  non-failing React `act(...)` and unmatched result-route warnings from the new
  duplicate-click regression test.
- Playwright enumerates **27 tests per project** and **81 total executions** across desktop,
  tablet, and mobile projects. Therefore, the previously reported **25/27** result refers to
  one project (consistent with desktop Chromium), not all three configured projects.
- A fresh desktop-Chromium rerun was attempted on 2026-07-26 using the isolated E2E database.
  It exceeded 30 minutes without returning a final summary and was terminated. The known
  offline-resilience test failed on both its initial attempt and retry: no `role="alert"`
  appeared within 20 seconds and the form remained in its disabled loading state. No other
  failure artifact was generated before termination. This rerun does **not** independently
  confirm the historical 25/27 total.
- The committed July 23 milestone report predates commits `bade48e`, `5c5d8f6`, and
  `bde709b`; its 101/101 frontend and 15/27 E2E figures are historical, not current.

### Known failures and risks

- Login/register E2E remains sensitive to the real IP-keyed rate limits (register 5/minute,
  login 10/minute). `frontend/playwright.config.ts` documents this and restricts execution
  to one worker, but heavy repeated runs can still cross a fixed-window limit.
- `frontend/e2e/resilience.spec.ts` offline-resilience case remains failing and was
  reproduced in this handoff inspection.
- The desktop 27-case suite can run for more than 30 minutes without a final result.
- Milestone 1 acceptance is still unmet: the repository requires 27/27 cases in at least two
  consecutive clean runs.
- A full unqualified `npx playwright test` means 81 project executions, not 27.

### Modified and untracked files

- Modified by this handoff: `PROGRESS.md`.
- Pre-existing untracked and not modified by this handoff:
  `.claude/settings.local.json`, `AGENTS.md`.
- Checkpoint 3 application/test files: none modified or untracked.
- Ignored test artifacts may exist under `frontend/test-results/` and in
  `backend/language_delay_e2e.db`; never stage or commit them.
- Suggested commit message, if the user later chooses to commit this documentation:
  `docs: add current agent handoff for milestone 1`

### Work still remaining

1. Obtain explicit approval to begin Checkpoint 3.
2. Diagnose the offline-resilience failure with the single focused desktop test and verify
   whether request abort/timeout handling reaches the child-form error UI.
3. Diagnose auth rate-limit behavior separately with focused login/register E2E runs; do
   not weaken production security controls merely to make tests pass.
4. Identify why the desktop suite does not terminate within 30 minutes.
5. Apply the smallest verified fix, run its focused unit/E2E tests, then run all 27 desktop
   cases twice from clean isolated E2E databases.
6. Only after the desktop baseline is stable, decide whether to execute the full
   three-project/81-execution matrix.

### Exact next recommended action

After explicit user approval for Checkpoint 3, run only the desktop offline-resilience test
against the isolated E2E server with a line or JSON reporter, capture the request/error state
at the 15-second client timeout, and determine whether the defect is in the test, fetch abort
handling, error mapping, or form mutation UI. Do not start with another full-suite run.

### Safety warnings

- Do not change branches, reset, clean, revert, discard, overwrite, commit, push, merge, or
  deploy automatically.
- Preserve `.claude/settings.local.json`, `AGENTS.md`, and this handoff change unless the user
  explicitly directs otherwise.
- Never stage or expose `.env` files, secrets, API keys, databases, `node_modules`, build
  output, logs, screenshots, traces, videos, Playwright artifacts, or temporary files.
- Preserve assessment scoring, specialist-referral rules, and all knowledge-base content
  unless a verified defect specifically requires an approved change.
- Work on Checkpoint 3 only, run focused tests after each code change, update this file, and
  stop before starting another checkpoint.

### Suggested prompt for the next coding agent

> Read `CLAUDE.md`, `PROGRESS.md`, `PROJECT_STATUS_AND_MILESTONES.md`, `PROJECT_SPEC.md`,
> and `CLAUDE_CODE_PROMPT.md`. Confirm the repository root, branch
> `feature/web-frontend`, `git status --short`, and recent log without changing Git state.
> Ask for approval, then work only on Milestone 1 Checkpoint 3: first reproduce and diagnose
> the focused desktop offline-resilience failure, then independently diagnose auth
> rate-limit flakiness and the non-terminating E2E run. Preserve scoring, referral rules,
> knowledge-base files, and all pre-existing work. Show a plan before code changes, run
> focused tests after every change, do not commit/push/merge/deploy, update `PROGRESS.md`,
> report every modified/untracked file, and stop before another checkpoint.
