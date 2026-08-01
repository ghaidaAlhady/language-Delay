# Implementation Plan

This session's scope was explicitly narrowed to **the FastAPI backend only** (Flutter
deferred). The plan below is the phase breakdown actually followed, each phase ending with a
full `pytest` + `ruff` + `mypy` pass before moving on.

## Phase 1 — Foundation
`pydantic-settings` config, `structlog` logging with sensitive-field redaction, async
SQLAlchemy engine + `UTCDateTime` type, Alembic wiring (async-aware `env.py`), consistent
error envelope + exception handlers, versioned router skeleton, CORS.

## Phase 2 — Knowledge-base ingestion & validation
Direct `.xlsx` loading (openpyxl/pandas) with structural validation (required sheets/columns),
typed Pydantic record normalization, activity-ID range parser, score-condition parser,
indexed `KnowledgeBaseRepository`. Validated against the real KB01–KB05 files, not synthetic
fixtures.

## Phase 3 — Auth & parent identity
`User`/`RefreshToken` models, Argon2 password hashing, JWT access tokens + opaque hashed
refresh tokens with rotation, register/login/refresh/logout/me/delete endpoints, `slowapi`
rate limiting on auth routes.

## Phase 4 — Child profiles
`Child` model, age computation from date of birth (not stored — always derived), full CRUD
with ownership isolation.

## Phase 5 — Assessment engine
`Assessment`/`AssessmentAnswer`/`AssessmentDomainResult` models, age-locked assessment start,
KB05 question retrieval, bulk answer upsert, deterministic scoring
(`app/services/scoring_service.py`) producing domain %, KB03-band severity/referral,
confidence, priority ordering, and strengths/support-needs — with full completion-gating and
history retrieval.

## Phase 6 — Activities & reports
KB02 activity/KB01 reference browse endpoints, deterministic Arabic report generation from
KB04 narrative templates, Arabic-shaped PDF export (`arabic_reshaper` + `python-bidi` +
ReportLab) with an embedded, packaged SIL-OFL Tajawal font and an optional
deployment-configurable override.

## Phase 7 — Weekly plan
7-day × 2-activity generation from KB03-suggested activities (worst-domain-first) with
round-robin top-up across domains, completion tracking + adherence calculation,
single-active-plan enforcement (soft-deactivate, not delete), alternative-activity swap.

## Phase 8 — Follow-up & reassessment
Uses 5–8 deterministic plan-linked questions from `knowledge_base/KB06.json`, selected by
age, goal/domain, and approved KB02 activity. Stores the exact question context and answers
against the owned active weekly plan, computes non-diagnostic weekly progress, and
idempotently generates the replacement plan through the existing weekly-plan service. KB05
remains exclusive to initial assessment.

## Phase 9 — Cross-cutting hardening
Request logging middleware (no PII/body logging), rate limits extended to the
compute-heavy "AI-equivalent" endpoints (assessment completion, report/plan/follow-up
generation).

## Phase 10 — Tests & documentation
Added `test_non_diagnostic.py` and `test_traceability.py` to close the two requirement gaps
not already covered incidentally by per-phase tests; filled in this `docs/` set.

## Deviations from a strictly-sequential build
Two issues were found and fixed mid-build rather than deferred, because they blocked
correctness of already-shipped phases:
1. SQLite naive/aware datetime bug (found during Phase 3 manual testing) — fixed with a
   `UTCDateTime` type decorator, applied retroactively to all existing timestamp columns.
2. Weekly-plan top-up fairness (found via a Phase 7 test failure) — switched from
   domain-by-domain fill to round-robin, so the "alternative activity" feature doesn't
   silently lose availability for whichever domain sorts first in KB02.

Both are documented in full in `DECISIONS_AND_ASSUMPTIONS.md`.

## Deferred (explicitly out of this session's scope)
See `IMPLEMENTATION_STATUS.md` for the complete list — chatbot, Google Sign-In, Flutter
mobile app, CI workflow, PRD.md/SRS.md (product-level docs; `PROJECT_SPEC.md` already serves
as the approved spec this session worked from).

## Milestone 2 — Safe Gemini-assisted wording

This later approved milestone extends the shipped React/FastAPI product; the backend-only
scope above is historical.

1. Add disabled-by-default typed Gemini settings and the official `google-genai`
   dependency.
2. Build provider-neutral contracts, three versioned prompt templates, an official async
   Gemini adapter, a production-disabled provider, and an E2E-only fake.
3. Build ownership-first, field-whitelisted context for completed assessments, existing
   weekly plans, and completed follow-ups.
4. Validate structured JSON, exact disclaimer, unsafe wording, URLs/markup, KB sources,
   activity names, and immutable deterministic facts.
5. Return useful deterministic Arabic fallback content for disabled/configuration/provider/
   validation failures without changing normal HTTP semantics for auth or resource errors.
6. Add three additive POST routes, request correlation, route-template logs, and rate
   limits. No database migration or generated-text persistence.
7. Add optional RTL assistance cards to the existing React result, plan, and follow-up
   pages. No browser provider SDK or key.
8. Add backend unit/API/privacy/fallback tests, frontend state/page tests, an isolated E2E
   fake-provider journey, and an opt-in live smoke test.
9. Update architecture, API, RAG, privacy, test, status, handoff, and operator
   documentation.
