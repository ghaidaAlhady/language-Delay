# Test Plan

## Tooling

`pytest` + `pytest-asyncio` (`asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed).
`ruff` for linting, `mypy` (strict-ish, with the `pydantic.mypy` plugin) for types. Run from
`backend/`:

```
pytest -q
ruff check app tests
mypy app
```

## Test isolation strategy

- **Knowledge base**: `tests/conftest.py`'s `kb_repository` fixture (session-scoped) loads
  the real `knowledge_base/*.xlsx` files once — tests exercise the actual supplied data, not
  synthetic fixtures, so a real KB error is a real test failure.
- **Database**: `db_session` fixture creates a fresh in-memory SQLite database
  (`sqlite+aiosqlite:///:memory:` with `StaticPool` so all connections share it) per test,
  with `PRAGMA foreign_keys=ON` enabled — cascading deletes are exercised for real, not
  assumed. Fully isolated from the developer's `language_delay.db`.
- **API**: `client` fixture wraps `TestClient(app)` with `get_db_session` overridden to the
  isolated `db_session` — full FastAPI dependency chain (including the KB-loading
  `lifespan`) runs for real.
- **Rate limiter**: `slowapi`'s storage is a process-wide singleton; an autouse
  `_reset_rate_limiter` fixture resets it before every test so one test's requests can't trip
  another's limit (this was a real bug found and fixed during this session).
- **User data**: all test fixtures use synthetic emails/names (`parent@example.com`,
  `"Layla"`) — never real personal data, per `SECURITY.md`.

## Coverage by layer

| Layer | Files | What's covered |
|---|---|---|
| KB parsing primitives | `test_kb_parsing.py` | ID-range shorthand (`A019-A025`), score-condition parsing, malformed-input rejection |
| KB loading/validation | `test_kb_loader.py` | Real-file load success; missing directory/file/sheet/column all raise `KnowledgeBaseLoadError` (synthetic malformed `.xlsx` built with `openpyxl` in `tmp_path`) |
| KB repository | `test_kb_repository.py` | Every query method against real data; decision-band boundary values at every edge (0, 49.999, 50, 69.999, 70, 84.999, 85, 100); unknown-ID lookups raise |
| Age computation | `test_age_service.py` | Exact-birthday edge cases; eligibility boundaries 0/1/2/3/4/5/6/12; future-DOB rejection |
| Scoring engine | `test_scoring_service.py` | All-max/all-min/mixed-domain scoring against real KB03 bands; confidence formula at boundaries vs. band center; the known KB01/KB05 milestone-link gap degrades gracefully |
| Auth (service + API) | `test_auth_service.py`, `test_auth_api.py` | Register/login/refresh-rotation/logout/delete; duplicate email, wrong password, expired/invalid/reused tokens |
| Children (service + API) | `test_child_service.py`, `test_children_api.py` | CRUD, partial update, **cross-user ownership isolation**, cascading delete on account deletion |
| Assessment (service + API) | `test_assessment_service.py`, `test_assessments_api.py` | Age-gate at start; answer upsert; unknown question ID rejected; completion requires all questions answered; double-completion conflict; ownership isolation |
| Reports (service + API + PDF) | `test_report_service.py`, `test_reports_api.py`, `test_pdf_service.py` | Requires completed assessment; idempotent generation; referral flag on severe cases; weekly timing normalization; packaged Arabic font coverage, shaping, and embedding; report ID/structure; ownership isolation |
| Weekly plan (service + API) | `test_weekly_plan_service.py`, `test_weekly_plans_api.py` | Exactly 7×2 structure with no duplicate activities; single-active-plan enforcement across regeneration; adherence calculation; alternative-activity swap, including the exhausted-domain edge case; ownership isolation |
| Follow-up (service + API) | `test_followup_service.py`, `test_followups_api.py` | Requires the exact owned, active weekly plan at or above 70% completion; deterministic 5–8-question KB06 selection and same-domain fallback; rejects missing/unknown answers and stale/wrong plans; never reuses KB05; persists context; auto plan replacement; idempotency; ownership isolation |
| Cross-cutting | `test_non_diagnostic.py`, `test_traceability.py` | Disclaimer present verbatim on every report; no diagnostic language anywhere in generated output or KB04 templates; every ID the API returns resolves to a real KB row with matching text |

This table records the original backend coverage layers. The current Milestone 2 collection
contains 204 nodes: **203 passed and 1 explicitly opt-in live Gemini test skipped** in
completed bounded runs. See `PROGRESS.md` and
`MILESTONE_2_GEMINI_IMPLEMENTATION_REPORT.md` for the exact current record.

## Explicit requirement checklist

- [x] Unit tests for decision rules, KB loading, age selection, scoring, activity selection,
      report generation, weekly-plan generation.
- [x] API integration tests for every implemented endpoint.
- [x] Invalid-input and boundary tests (ages below 2, above 5, and every band boundary).
- [x] Missing and malformed knowledge-base data.
- [x] The system does not produce a medical diagnosis (`test_non_diagnostic.py`).
- [x] All recommendations are traceable to real KB records (`test_traceability.py`).
- [x] Realistic synthetic data only.
- [x] Full suite run after every phase (see session history — 39 → 59 → 90 → 118 → 134 → 146
      → 154 → 158 tests across the ten phases).

## Not covered by the current automated suite (see `IMPLEMENTATION_STATUS.md`)
- Load/performance testing.
- Flutter widget/integration tests (no mobile app yet).
- Live hosted-environment smoke tests against the final Netlify, Render, and Neon URLs.

The repository now includes `.github/workflows/ci.yml` for backend and frontend checks on
push/pull request. Live Gemini remains explicitly excluded from CI.

## Milestone 2 AI-assistance coverage

Backend focused scenarios cover:

- default-disabled and incomplete-configuration behavior;
- production rejection of the E2E fake provider;
- strict valid JSON and malformed/extra-field rejection;
- exact disclaimer enforcement;
- diagnostic, medication, treatment, URL, HTML, and code-fence rejection;
- unknown/duplicate sources, unsupported tips, missing exact activity names, and invented
  activity IDs;
- severity, referral, progress, and percentage contradictions;
- deterministic fallback grounding;
- authentication on all three endpoints;
- ownership masking on assessment, plan, and follow-up before provider invocation;
- provider timeout, generic failure, malformed JSON, unsafe output, and ungrounded output
  returning HTTP 200 fallback;
- resource-state validation, rate limiting, correlation header, PII/resource-ID exclusion,
  no answer-history/notes context, and unchanged authoritative assessment data.

Frontend tests cover loading, Gemini, deterministic fallback, retryable fallback, disabled
fallback, network error/retry, and integration on all three existing pages while their
deterministic content remains visible. Playwright uses `APP_ENV=e2e` plus
`AI_TEST_PROVIDER=fake`; production ignores that provider selection. The focused journey
exercises three valid provider surfaces and a deliberate timeout fallback without a real
key.

`backend/tests/test_live_gemini.py` is opt-in only:

```powershell
$env:RUN_LIVE_GEMINI_TEST = "1"
$env:GEMINI_API_KEY = "<local secret>"
$env:GEMINI_MODEL = "<model available to your Google AI project>"
Set-Location .\backend
.\.venv\Scripts\python.exe -m pytest -q -s tests/test_live_gemini.py
```

It skips unless explicitly enabled and configured, and never prints the key, prompt, or
provider output. Final suite counts are recorded in `PROGRESS.md` and the milestone report.

## Milestone 3 coverage

New backend test files: `test_followup_ai_questions.py` (valid 5/8-question output, keeping
only 5 of a larger candidate pool, every failure mode → deterministic fallback with the
correct `fallback_reason`, database-frozen/identical set across repeat calls and simulated process-cache clearing with the replacement provider never called, identical deterministic score whether questions were AI-worded or not, zero PII
in the provider context), `test_activity_explanation_api.py` (valid grounded explanation with
3–5 steps, ownership masked as 404 before any provider call, every failure mode → KB02
fallback, zero session data in context), `test_source_references.py` (label resolution, neutral
fallback for an unknown ID, an existing AI-summary endpoint's response includes resolved
`source_references`). Existing `test_followup_service.py`/`test_followups_api.py` gained the
70% boundary matrix (7/10, 9/14, 10/14, 14/14, 0/0) and a regression test locking in the exact
`submit(..., expected_questions=...)` call shape the API route uses (a prior bug referenced an
unassigned local variable on that path). `tests/conftest.py` gained an autouse fixture
defaulting every test's AI provider to `DisabledAIProvider`, independent of the local machine's
`backend/.env`.

Frontend: `eligibility.test.ts` (the full backend-mirrored boundary matrix),
`SourceReferenceDisclosure.test.tsx` (collapsed by default, mouse and keyboard expand, human-
readable label with the raw ID as secondary/title text, neutral fallback label),
`ActivityExplanationCard.test.tsx` (loading, full success render, deterministic-fallback
label, safe generic error+retry), plus additions to `WeeklyPlanPage.test.tsx` (70%-eligible,
below-70% disabled + exact message, exactly-70%-eligible, persisted backend-driven
in-progress resume label, alternative-button freeze after reassessment starts, and
"افهم أكثر" fetch-once/duplicate-click prevention) and
`ReassessmentPage.test.tsx` (70%-vs-100% eligibility gate text, the AI transparency note).
`AiAssistanceCard.test.tsx` was updated to assert the new collapsed source disclosure instead
of the old raw comma-separated `source_ids` line.

One new focused E2E, `frontend/e2e/milestone3-ai-followup-and-explanation.spec.ts`, exercises
the full flow (70% gate → reassessment → frozen questions across reload → "افهم أكثر" →
source disclosure → unchanged deterministic scores/goal/referral) against the isolated E2E
backend with `AI_TEST_PROVIDER=fake`, extending `FakeAIProvider` with the two new operations.
Exact pass/fail counts for this session's runs are recorded in `PROGRESS.md` and the milestone
report, not duplicated here to avoid drift.


## Deployment-focused tests

- Database URL normalization: SQLite unchanged; `postgres://` / `postgresql://` become `postgresql+asyncpg`, `sslmode` is translated, and unsupported `channel_binding` is removed.
- Frozen reassessment set remains identical after clearing the process cache and replacing the provider.
- `WeeklyPlanResponse.reassessment_started` drives resume UX.
- Backend availability gate waits for `/health` before mounting authentication.
- Alternative activity returns a different approved same-domain activity even when every domain item is already represented in the plan.
- PDF unit coverage verifies sanitizer behavior, packaged Arabic font registration, shaping, embedding, and valid PDF structure. A final visual render-to-image inspection remains a required local release check because the sanitized review environment does not contain every PDF runtime dependency.
