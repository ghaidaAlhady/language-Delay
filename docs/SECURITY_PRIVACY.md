# Security & Privacy

## Authentication

- Passwords hashed with **Argon2** (`passlib`, `app/security/passwords.py`) — memory-hard,
  resistant to GPU cracking. Never stored or logged in plaintext.
- Access tokens: short-lived JWTs (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30), HS256, signed
  with `SECRET_KEY`. Contain only `sub` (user ID), `type`, `iat`, `exp` — no PII.
- Refresh tokens: opaque, high-entropy random strings (`secrets.token_urlsafe(48)`), **not**
  JWTs. Only a SHA-256 hash is persisted (`RefreshToken.token_hash`); the plaintext is
  returned to the client once and never stored. Rotates on every use (old token revoked
  server-side); individually revocable on logout without a JWT blocklist.
- `SECRET_KEY` has no default — the app refuses to start without one (`Settings.secret_key`
  is a required field), preventing an accidentally-insecure deployment.

## Authorization / ownership isolation

Every child-scoped resource (assessments, reports, weekly plans, follow-ups) is reached only
through an ownership check that walks the chain back to `child.user_id == current_user.id`.
A mismatch or missing record both return `404` (never `403`) so a caller cannot distinguish
"doesn't exist" from "belongs to someone else" — verified for every resource type in
`test_*_api.py::test_*_ownership_isolation`.

## Input/output validation

Every request and response is a typed Pydantic v2 model. Examples of validated boundaries:
email format (`EmailStr`), password length (8–128 chars), date-of-birth not in the future,
assessment age locked to 2–5, response values restricted to a 5-member enum, activity/question
IDs checked against the real KB set before being accepted.

## Rate limiting

`slowapi`, keyed by remote address (`app/core/rate_limit.py`):

| Endpoint group | Limit |
|---|---|
| `POST /auth/register` | 5/minute |
| `POST /auth/login` | 10/minute |
| `POST /auth/refresh` | 20/minute |
| Assessment completion, report/weekly-plan/follow-up generation ("AI-equivalent" compute) | 20/minute each |

A breach returns `429` via the same JSON error envelope as every other error.

## Logging

- Structured JSON logs (`structlog`), never plaintext string interpolation of user data.
- `RequestLoggingMiddleware` logs method, path, status code, and duration for every request —
  **never** the request/response body, query string, or headers, so tokens, passwords, and
  free-text answers never reach the logs even indirectly.
- `_redact_sensitive` (`app/core/logging.py`) redacts any log field literally named
  `password`, `hashed_password`, `access_token`, `refresh_token`, `token`, `authorization`,
  `secret_key`, `llm_api_key`, `gemini_api_key`, `prompt`, `raw_prompt`, `raw_response`,
  `provider_response`, `ai_context`, `answer_text`, `message`, `report_text`, or `notes`,
  as a defense-in-depth backstop even if a future call site logs one of these by mistake.
- Unhandled exceptions are logged server-side with `exc_info` but returned to the client as a
  generic `"An unexpected error occurred."` — stack traces never leak.

## Error responses

Consistent envelope everywhere: `{"error": {"code", "message", "details"}}`. `code` is a
short machine-readable slug (`not_found`, `unauthorized`, `conflict`, `validation_error`,
`bad_request`, `service_unavailable`, `internal_error`); `message` is safe to show a user;
`details` carries structured extra context only where useful (e.g. which question IDs are
missing), never raw exception text.

## CORS

Configured per environment via `CORS_ORIGINS` (JSON array in `.env`); the middleware is only
added if at least one origin is configured — no wildcard default.

## Secrets management

- `.env` is git-ignored (`.gitignore`: `.env`, `.env.*`, `!.env.example`); only
  `backend/.env.example` (placeholder values) is committed.
- No API keys, passwords, or real child/parent data are committed anywhere in this session's
  changes. `backend/.env` (this developer's local secret key, randomly generated) exists only
  on disk, never staged.
- SQLite database files (`*.db`), generated PDFs, logs, `.env` files, and build/test artifacts are git-ignored. Production `DATABASE_URL`, Gemini keys, and CORS origins are entered only in hosting dashboards.

## Data minimization / retention

- Child profiles collect only the fields `PROJECT_SPEC.md` specifies — no unnecessary PII.
- Assessments, reports, and follow-ups are **never deleted** except via explicit
  child/account deletion (cascading, user-initiated). Weekly plans are the one exception —
  superseded plans are soft-deactivated, not hard-deleted, preserving an audit trail while
  satisfying "only the latest is active."
- Timestamps are always stored and returned in UTC.

## Non-diagnostic guarantee

Every generated report carries the fixed disclaimer text
(`app/core/constants.py::DISCLAIMER_AR`) verbatim — the same string on every report, not
paraphrased per case. `tests/test_non_diagnostic.py` asserts this and additionally asserts
that no report field, and none of the five KB04 narrative templates, contains the word
"تشخيص" (diagnosis) outside the disclaimer's own explicit denial of diagnosing.

## Deferred to a future session

- Google Sign-In server-side ID-token verification (needs the `google-auth` dependency and a
  live client ID/secret — see `docs/DECISIONS_AND_ASSUMPTIONS.md`).
- Consent-acknowledgment endpoint before first assessment (`CLAUDE_CODE_PROMPT.md` mentions
  this; not in this session's explicit endpoint list).
- Privacy policy / terms-of-use version acknowledgment endpoints.
- A secrets scan / dependency vulnerability scan step in CI (no GitHub Actions workflow was
  added this session — see `IMPLEMENTATION_STATUS.md`).

## Gemini-assisted wording privacy boundary (Milestone 2)

- Disabled by default; a call is possible only when the enable flag, server-side API key,
  and model are all configured.
- Provider configuration is backend-only. No SDK, API key, prompt, or raw provider response
  is shipped to browser code.
- Ownership is checked before context construction. Foreign and nonexistent resources are
  both `404`, and the provider is not called.
- Context builders whitelist only age band, deterministic output, approved goals/progress,
  and KB source IDs/excerpts. Names, emails, user/child/resource IDs, tokens, full answer
  history, notes, medical history, and secrets are never included.
- The request logger now emits the FastAPI route template rather than the concrete URL path,
  adds an opaque correlation ID and `X-Request-ID`, and never logs query/body/header data.
- AI orchestration logs only correlation ID, operation, prompt version, provider label,
  latency, outcome, source/tip counts, and normalized fallback reason. Prompts, context,
  responses, provider exception details, generated health wording, PII, and resource IDs are
  prohibited and protected by global redaction keys.
- Strict structured output is validated for schema, exact disclaimer, unsafe language,
  external URLs/markup, KB grounding, exact activity name/source binding, and contradiction
  of immutable severity/referral/progress facts.
- Provider failure is fail-closed to deterministic wording and never changes the underlying
  resource.

## Milestone 3 additions to the privacy boundary

- The follow-up-question-variation operation's context is a deterministic KB06 candidate list
  (id, domain, activity name, original wording) only — no child, parent, or answer-history
  data is included; the candidates themselves never contain PII since they're KB06 templates.
- The activity-explanation operation's context is built from a single KB02 `ActivityRecord`
  only. Its context builder never queries the child, assessment, weekly-plan, or session
  tables, so PII exclusion holds structurally, not by a redaction step that could be missed.
- Both new operations reuse the existing `_redact_sensitive` structlog processor and
  `REDACTED_KEYS` list unchanged — no new logging code paths were added, only new callers of
  the same `logger.info(...)`-with-safe-fields pattern already used by `orchestration.py`.
- Every routine backend test now runs with `app.dependency_overrides[get_ai_provider]`
  defaulted to a network-free `DisabledAIProvider` (an autouse fixture in `tests/conftest.py`),
  so no automated test run can silently depend on — or exhaust the quota of — whatever a
  developer's local `backend/.env` happens to have configured for manual Gemini verification.
- Source-reference labels are resolved only from the approved KB context server-side; Gemini
  is never asked for, and cannot supply, a label.


## Hosted beta controls

- Netlify receives only the public `VITE_API_BASE_URL`; Gemini credentials remain backend-only.
- Render generates `SECRET_KEY`; other secrets are marked `sync: false` in `render.yaml`.
- CORS must contain the exact Netlify HTTPS origin, never `*` for this authenticated app.
- PostgreSQL replaces ephemeral SQLite storage on free hosting.
- The readiness endpoint checks database connectivity without exposing configuration.
- The cold-start gate sends only an unauthenticated `GET /health`; it never includes tokens or user data.
