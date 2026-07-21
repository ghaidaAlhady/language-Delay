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
| Reports (service + API + PDF) | `test_report_service.py`, `test_reports_api.py`, `test_pdf_service.py` | Requires completed assessment; idempotent generation; referral flag on severe cases; PDF is a real, valid file with and without a configured font; ownership isolation |
| Weekly plan (service + API) | `test_weekly_plan_service.py`, `test_weekly_plans_api.py` | Exactly 7×2 structure with no duplicate activities; single-active-plan enforcement across regeneration; adherence calculation; alternative-activity swap, including the exhausted-domain edge case; ownership isolation |
| Follow-up (service + API) | `test_followup_service.py`, `test_followups_api.py` | Requires a completed assessment *and* a previous one; improvement detection; auto plan regeneration; idempotency; ownership isolation |
| Cross-cutting | `test_non_diagnostic.py`, `test_traceability.py` | Disclaimer present verbatim on every report; no diagnostic language anywhere in generated output or KB04 templates; every ID the API returns resolves to a real KB row with matching text |

**158 tests, all passing** as of the end of this session (`pytest -q`).

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

## Not covered this session (see `IMPLEMENTATION_STATUS.md`)
- Load/performance testing.
- Flutter widget/integration tests (no mobile app yet).
- A CI workflow to run this suite automatically on push (no `.github/workflows/` file was
  added — `PACKAGE_MANIFEST.txt`/repo root has no existing CI config to extend).
