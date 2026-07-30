# Project Status and Milestones

Authoritative update: 2026-07-28

Repository: `C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub`

Branch: `feature/web-frontend`

Latest commit at verification start: `bbb896264ea35378086a825769725f9c0ae6cedd`

## Current status

The FastAPI backend and Arabic-first React web frontend implement the approved MVP parent
journey: authentication, child profiles, assessment, deterministic results and reports,
weekly plans, weekly follow-up, progress comparison, PDF export, and persisted data.

Milestone 1 stabilization and its focused corrections are present at the current `HEAD`.
Milestone 2 optional Gemini-assisted wording is implemented in the working tree and has
completed backend, frontend, and focused fake-provider verification. It is not committed or
staged. The earlier Milestone 1 final gate—27/27 Desktop/Chromium E2E tests in two
consecutive clean isolated runs—has still not been demonstrated.

## Milestone 1 checkpoints

| Checkpoint | Status | Verified outcome |
|---|---|---|
| Checkpoint 1 | Completed | Baseline captured and E2E environment isolated from development data. |
| Checkpoint 2 | Completed | Authentication and core E2E flows stabilized without weakening security. |
| Checkpoint 2.1 | Completed | Final-question duplicate assessment submission race resolved. |
| Checkpoint 3 | Completed, committed, and pushed | Weekly follow-up persistence and replacement-plan linkage verified; commit `638b324`. |
| Checkpoint 4 | Completed locally; awaiting review | Final regression, offline fix, reports, manual guide, cleanup, and handoff completed. |

## Current verified results

| Verification | Result |
|---|---|
| Backend tests | 203 passed and 1 opt-in live test skipped across bounded groups; see environment caveat below. |
| Frontend tests | 117/117 passed in 24 files. |
| Frontend type-check | Passed. |
| Frontend lint | Passed with one pre-existing warning at `src/tests/test-utils.tsx:58`. |
| Frontend production build | Passed. |
| Focused fake-provider Gemini E2E | 1/1 passed, covering three assisted surfaces and deterministic timeout fallback. |
| Critical Desktop E2E flows | All passed across a 4/5 combined run and isolated login-flake retry. |
| Weekly follow-up Case 10 | Passed in Checkpoint 4; Checkpoint 3 recorded 5/5 focused runs. |
| Focused offline E2E | Passed after a narrow create-child mutation fix. |
| Full Desktop/Chromium E2E | Not rerun for Milestone 2 because the critical run reproduced known login flakiness; the latest pre-Milestone-2 record remains 26/27 with its sole login failure passing alone. |

The Windows backend runner has intermittent long-process hangs. All 204 collected nodes
completed in bounded groups: 203 passed and the explicitly opt-in live test skipped. No
backend assertion failure was found.

## Checkpoint 4 defect classification

The offline E2E failure was an application defect, not a selector failure. TanStack Query
paused the create-child mutation while offline before the API client could return the
existing Arabic offline error. The narrow fix sets only that mutation to
`networkMode: "always"`. A new hook regression test and the focused offline E2E both pass.

The single full-suite failure is classified as Windows/browser connection flakiness:
the UI reported a network failure during login while the isolated backend logged HTTP 200,
and the exact test passed immediately when rerun alone. The session also produced delayed
Playwright server startup, a client `EADDRINUSE` error, and a large port-8001 TIME_WAIT
backlog.

## Isolation and safety status

- E2E backend: `127.0.0.1:8001`.
- E2E frontend: `127.0.0.1:4173`.
- E2E database: disposable `backend/language_delay_e2e.db`.
- Manual backend: `127.0.0.1:8000`.
- Manual frontend: normally `http://localhost:5173`.
- The development database retained its original size and modification time.
- Checkpoint 4 test servers were stopped and generated test artifacts were removed.
- Production rate limiting was not disabled or weakened.
- Assessment scoring, specialist-referral rules, and KB01–KB05 were not changed.
- No `.env` file, secret, API key, or database is part of the Checkpoint 4 change set.

## Known issues and risks

1. The two-consecutive-clean-run Milestone 1 gate remains open.
2. Login/register can remain flaky under heavy repeated E2E load because real rate limits
   are intentionally retained.
3. The Windows Python bytecode/process environment should be refreshed before the final
   acceptance reruns.
4. Frontend unit tests still print pre-existing non-failing React `act(...)` and
   unmatched-route diagnostics.
5. Lint still reports one pre-existing non-failing export warning.

## Exact next action

Review the unstaged Milestone 2 implementation, this status file,
`MILESTONE_2_GEMINI_IMPLEMENTATION_REPORT.md`, and the latest `PROGRESS.md` handoff. If
approved, stage only the documented Milestone 2 paths and keep all local settings, secrets,
databases, and generated artifacts excluded. A future Milestone 1 acceptance session may
still run Desktop Chromium twice from fresh isolated E2E databases; do not use the
development database for that gate.

## Milestone 2 — Safe Gemini-assisted explanations

Milestone 2 was explicitly approved and implemented on `feature/web-frontend` on
2026-07-28. It adds optional server-side wording assistance for a completed assessment,
existing weekly plan, and completed weekly follow-up.

The milestone does not add a chatbot or autonomous agent and does not alter deterministic
assessment scoring, severity, referral, eligibility, KB activities, weekly-plan generation,
or follow-up calculations. Provider calls are disabled by default, privacy-minimized,
strictly validated, and fail to deterministic Arabic wording.

See `MILESTONE_2_GEMINI_IMPLEMENTATION_REPORT.md` and the latest `PROGRESS.md` handoff for
the exact verification/commit state. Do not start another milestone automatically.
