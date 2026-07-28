# Milestone 1 Stabilization Report

Report date: 2026-07-26

Branch: `feature/web-frontend`

Checkpoint: 4 — Final Regression, Documentation, and Manual Testing Readiness

## Objective

Milestone 1 stabilizes the implemented backend and React web frontend, verifies the
critical parent journey against an isolated E2E environment, resolves confirmed
release-blocking defects without changing approved decision logic, and prepares accurate
manual-testing and handoff documentation.

## Completed checkpoints

- Checkpoint 1: baseline and E2E isolation.
- Checkpoint 2: authentication and core-flow E2E stabilization.
- Checkpoint 2.1: assessment final-question duplicate-submission race fix.
- Checkpoint 3: weekly follow-up persistence, plan linkage, duplicate protection, and Case
  10 verification.
- Checkpoint 4: final regression, focused offline diagnosis/fix, documentation, generated
  artifact cleanup, and manual-testing readiness review.

## Major defects fixed

- E2E tests now use backend port 8001, frontend port 4173, and a disposable database rather
  than the development database.
- Authentication/assessment E2E setup was serialized and isolated without weakening
  production security or rate limits.
- The final assessment question is protected from rapid duplicate completion.
- Weekly follow-up requires the correct prior active plan, persists one follow-up,
  generates a linked replacement plan, and survives reload.
- The offline child-creation submission previously remained paused indefinitely inside
  TanStack Query. `useCreateChild` now uses `networkMode: "always"` so the existing API
  error mapping can show the Arabic offline message. A hook regression test covers this.

## Final verification results

- Backend: 168 tests collected; all 168 passed across bounded file/logical groups.
  The host virtual environment contains corrupted pandas bytecode (`bad marshal data`) and
  long monolithic pytest processes intermittently hung on this Windows session. A
  task-local `PYTHONPYCACHEPREFIX` bypassed the corrupted cache without modifying the
  environment. No backend test failure was found.
- Frontend: 107/107 tests passed in 22 files after the offline regression test was added.
- TypeScript type-check: passed.
- Lint: passed with one pre-existing non-failing
  `react(only-export-components)` warning at `src/tests/test-utils.tsx:58`.
- Production build: passed.
- Critical Desktop/Chromium flows: registration/login, child creation, initial assessment,
  result, weekly plan, weekly follow-up, replacement plan, and reload persistence passed
  across the focused run and individual reruns.
- Weekly follow-up Case 10: passed in Checkpoint 4; Checkpoint 3 also recorded five
  consecutive clean focused successes.
- Offline resilience: focused E2E passed after the narrow fix.
- Complete Desktop/Chromium run with retries disabled: 26/27 passed in 4.6 minutes. The
  only failure was a transient browser connection error during login while the backend
  recorded HTTP 200; that exact test passed immediately when rerun alone.
- A second complete desktop run was not started because the first was not a reliable clean
  result and the Windows environment showed E2E server startup delays, an `EADDRINUSE`
  client error, and a large port-8001 TIME_WAIT backlog.

## E2E isolation design

`backend/run_e2e_server.py` sets the database URL to
`backend/language_delay_e2e.db`, deletes only that disposable file at startup, applies
Alembic migrations, and serves on `127.0.0.1:8001`. Playwright serves the E2E frontend on
`127.0.0.1:4173` and points it to port 8001. Normal manual development remains on backend
port 8000 and normally frontend port 5173.

The development database retained its original size and UTC modification time
(`520192` bytes; `2026-07-23 19:55:48Z`) throughout Checkpoint 4. The disposable E2E
database and generated test artifacts were removed after verification.

## Known remaining failures and risks

- No focused functional test remains failing.
- Milestone 1's repository acceptance gate of 27/27 desktop tests in two consecutive clean
  isolated runs remains unmet. The only full-run failure passed individually and is
  classified as Windows/browser connection flakiness, not a confirmed application defect.
- Real login/register rate limits remain a risk under heavy repeated E2E load. No
  production security control was disabled or weakened; the final full-run failure was a
  connection error, not HTTP 429.
- The current Python virtual environment has stale/corrupted bytecode and intermittent
  long-process behavior. Recreating the virtual environment in a separately approved
  maintenance step is preferable to relying on a temporary cache prefix.
- The pre-existing React test `act(...)` and unmatched-route diagnostics remain
  non-failing.

## Security, privacy, and decision safeguards

- No `.env` file, secret, API key, token, database, personal data, or provider integration
  was added or staged.
- Assessment scoring and specialist-referral implementation were not changed.
- KB01–KB05 content was not changed.
- Production authentication and rate limiting were not weakened.
- User-facing medical guidance remains explicitly non-diagnostic.
- Gemini work is limited to a documentation proposal; no model, package, key, or code was
  added.

## Acceptance and readiness

Checkpoint 4's investigation, narrow defect fix, regression work, documentation, and
cleanup are complete. The application is ready for structured local manual testing using
the development database and `MANUAL_FRONTEND_TESTING_GUIDE.md`.

Milestone 1 is **not formally accepted yet** because the required two consecutive clean
27/27 Desktop/Chromium runs have not been obtained. The branch is ready for Checkpoint 4
review, but the exact next verification action is to use a fresh Windows session and
healthy Python virtual environment, then run the complete desktop project twice from fresh
isolated E2E databases with retries disabled.

Milestone 2 proposal review/planning may begin after user review, but implementation must
not begin until Milestone 1 is accepted and separately approved.
