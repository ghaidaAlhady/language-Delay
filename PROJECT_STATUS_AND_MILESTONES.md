# Project Status and Milestones

Authoritative update: 2026-07-26

Repository: `C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub`

Branch: `feature/web-frontend`

Latest commit at verification start: `638b324ccd9b52ee424d1d584bd4c1580b96c134`

## Current status

The FastAPI backend and Arabic-first React web frontend implement the approved MVP parent
journey: authentication, child profiles, assessment, deterministic results and reports,
weekly plans, weekly follow-up, progress comparison, PDF export, and persisted data.

The project is in Milestone 1 final stabilization. Checkpoint 4 implementation and
documentation work is complete locally and awaiting review. Milestone 1 is not formally
accepted because the repository's final gate—27/27 Desktop/Chromium E2E tests in two
consecutive clean isolated runs—has not yet been demonstrated.

No Gemini integration is implemented. `MILESTONE_2_GEMINI_PROPOSAL.md` is documentation
only.

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
| Backend tests | 168/168 passed across bounded groups; see environment caveat below. |
| Frontend tests | 107/107 passed in 22 files. |
| Frontend type-check | Passed. |
| Frontend lint | Passed with one pre-existing warning at `src/tests/test-utils.tsx:58`. |
| Frontend production build | Passed. |
| Critical Desktop E2E flows | Passed across focused run and individual reruns. |
| Weekly follow-up Case 10 | Passed in Checkpoint 4; Checkpoint 3 recorded 5/5 focused runs. |
| Focused offline E2E | Passed after a narrow create-child mutation fix. |
| Full Desktop/Chromium E2E | 26/27 passed; sole transient login connection failure passed individually. |
| Second full Desktop run | Not run because the first result and Windows environment were not stable enough to make it trustworthy. |

The backend virtual environment has corrupted cached pandas bytecode and intermittent
long-process hangs. All 168 collected tests passed when executed in bounded groups with a
task-local bytecode-cache prefix; no backend application failure was found. This
environment should be recreated or repaired in a separately approved maintenance task.

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

Review the Checkpoint 4 changes. In a fresh Windows session with a healthy recreated Python
virtual environment, verify ports 4173 and 8001 are free, then run the complete
Desktop/Chromium E2E project twice consecutively with retries disabled and a freshly
created isolated E2E database for each run. If both runs are 27/27, update the reports to
mark Milestone 1 accepted.

Do not reset or use the development database for this gate.

## Next milestone

After Milestone 1 acceptance and explicit user approval, the next milestone is Milestone 2:
review and refine the safe Gemini-assistance proposal. Milestone 2 is not implemented and
must not begin automatically. Manual frontend testing may proceed before that gate using
`MANUAL_FRONTEND_TESTING_GUIDE.md`.
