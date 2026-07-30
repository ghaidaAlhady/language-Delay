# Implementation Status

Scope of this session: **FastAPI backend only**, per explicit instruction. Flutter was not
touched.

## Completed

### Foundation
- [x] Config, structured logging (with redaction), async SQLAlchemy + Alembic, consistent
      error envelope, versioned router, CORS, request-logging middleware, rate limiting.

### Knowledge base
- [x] Direct `.xlsx` loading + structural validation for KB01–KB05 plus structured JSON
      loading for KB06, typed normalization, indexed repository, activity-ID range parser,
      and score-band parser. Validated against the real supplied files.
- [x] **Data-integrity issue found and reported**: KB01/KB05 milestone-ID scheme mismatch for
      ages 3–5 (see `DECISIONS_AND_ASSUMPTIONS.md`). Backend degrades gracefully per
      user-approved direction; KB files were not modified.

### Auth
- [x] Register, login, refresh (rotating), logout, current-user, account deletion
      (cascading). Argon2 passwords, JWT access tokens, opaque hashed refresh tokens.
- [ ] Google Sign-In — deferred (needs `google-auth` dependency + live client credentials;
      not stubbed, since a non-functional endpoint would violate the no-placeholder rule).

### Children
- [x] Full CRUD, computed age + assessment-eligibility, ownership isolation.

### Assessment
- [x] Age-locked start, KB05 question retrieval (both assessment-scoped and standalone by
      age), bulk answer upsert, deterministic scoring, completion gating, full history.

### Reports
- [x] Deterministic Arabic report generation (KB04-grounded), idempotent generation, list/
      detail retrieval, and Arabic-shaped PDF export with an embedded packaged Tajawal font.
- [ ] English report generation — deferred; KB04 templates are Arabic-only, and translating
      them would mean inventing content not in the supplied KB (see
      `DECISIONS_AND_ASSUMPTIONS.md`).

### Weekly plan
- [x] Exactly 7×2 generation, single-active-plan enforcement, completion + adherence,
      alternative-activity suggestion.

### Follow-up / reassessment
- [x] Plan-linked 5–8-question KB06 selection, persisted answer/question context,
      deterministic non-diagnostic weekly progress, ownership isolation, idempotent
      submission, and automatic replacement-plan generation. KB05 is not reused.

### Activities & references
- [x] Age/domain browse, assessment-scoped recommended-activity resolution, KB01 reference
      list.

### Cross-cutting
- [x] Rate limiting (auth + compute-heavy endpoints), request logging without PII,
      ownership isolation verified for every resource type, non-diagnostic guarantee
      verified by test.

### Testing
- [x] 158 tests (unit, service, and API-integration levels) — see `TEST_PLAN.md` for the
      full breakdown. All passing.

### Documentation
- [x] `API_SPEC.md`, `DATABASE_SCHEMA.md`, `ARCHITECTURE.md` (with Mermaid diagrams),
      `RAG_AI_DESIGN.md`, `SECURITY_PRIVACY.md`, `TEST_PLAN.md`, `IMPLEMENTATION_PLAN.md`,
      `DECISIONS_AND_ASSUMPTIONS.md`, this file.

## Deferred (not part of this session's scope)

- **Flutter mobile app** — this session's instructions explicitly stopped before Flutter.
- **Chatbot** — not in this session's explicit endpoint list; a substantial separate feature
  (domain-classifier guard, conversation history, RAG-grounded free-text responses).
- **Google Sign-In** — see above.
- **Privacy policy / terms-of-use acknowledgment endpoints** — mentioned in
  `CLAUDE_CODE_PROMPT.md` but not in this session's explicit endpoint list.
- **`PRD.md` / `SRS.md`** — left as placeholders. `PROJECT_SPEC.md` already serves as the
  approved product specification this session worked from; writing a separate PRD/SRS is
  product-requirements documentation work, not backend implementation, and was judged out of
  this session's scope. Recommend a dedicated pass if these are needed.
- **CI workflow** (`.github/workflows/`) — no GitHub Actions file was added. The repository
  has no pre-existing CI to extend; adding one is a reasonable next step but wasn't part of
  the explicit backend-implementation ask.
- **Rate limiting on read-heavy GET endpoints** — only auth and the compute-heavy
  generation/completion endpoints are rate-limited; this matches "rate-limit authentication
  and AI endpoints" literally rather than rate-limiting everything.

## Known limitations

- **KB01/KB05 milestone-ID gap for ages 3–5** (see `DECISIONS_AND_ASSUMPTIONS.md`) — narrows
  the strengths/support-needs skill-name list for those ages; does not affect scoring,
  severity, referral, or activity recommendations.
- **PDF Arabic rendering requires a deployment-supplied font** (`PDF_ARABIC_FONT_PATH`) — no
  font ships in the repo (licensing). Without one configured, PDFs generate successfully but
  Arabic text renders illegibly.
- **Report numbering** (`REP-0001`…) is a simple count-based sequence, not safe under
  concurrent writers — acceptable for SQLite/single-process MVP, would need a DB sequence or
  similar for a multi-instance deployment.
- **No load/performance testing** has been done.

## Final verification (this session)

- [x] Full test suite passes: `pytest -q` → 158 passed.
- [x] `ruff check app tests` → all checks passed.
- [x] `mypy app` → no issues found (67 source files).
- [x] Alembic migrations apply cleanly from an empty database (`alembic upgrade head`, six
      migrations in sequence).
- [x] FastAPI app starts successfully and loads the real knowledge base at startup.
- [x] OpenAPI docs (`/docs`, `/openapi.json`) load with all 30 endpoints registered.

## How to run locally

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat for cmd
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # then set SECRET_KEY to a real random value
alembic upgrade head
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs`. Run tests with `pytest -q` (auto-creates an isolated
in-memory database per test; does not touch the dev SQLite file).

## Current status addendum — Milestone 2

The repository now includes the React web frontend and the optional server-side Gemini
wording checkpoint. The earlier “Flutter not touched / no LLM call” statements describe the
original backend session and are not current product status.

Completed:

- [x] Three ownership-scoped assistance endpoints for assessment, weekly plan, and follow-up.
- [x] Official `google-genai` adapter behind a provider-neutral interface.
- [x] Disabled-by-default feature flag and useful deterministic fallback for every provider
      failure category.
- [x] Strict Pydantic JSON contract, safety checks, KB source/activity grounding, exact
      disclaimer, and immutable severity/referral/progress checks.
- [x] Whitelisted privacy-minimized contexts with no parent/child identity, resource IDs,
      answer history, notes, medical history, or secrets.
- [x] Safe request correlation and route-template/AI operational logging.
- [x] Optional RTL assistance sections on all three existing React pages.
- [x] Backend, frontend, fake-provider E2E, and opt-in live-smoke test coverage.
- [x] No migration, generated wording persistence, chatbot, autonomous agent, or change to
      deterministic scoring/referral/activity/plan/follow-up logic.

Gemini remains unavailable until an operator explicitly sets `GEMINI_ENABLED=true`,
`GEMINI_API_KEY`, and `GEMINI_MODEL` in a local/deployment secret environment. The local
development virtual environment used for final verification has `google-genai==1.75.0`
installed from the declared `requirements.txt` range. The adapter constructor and async
close path were verified without making a generation request. Deployments must still run
`pip install -r backend/requirements.txt`; no key or model is committed.
