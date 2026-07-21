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
  `secret_key`, `llm_api_key`, `answer_text`, `message`, `report_text`, or `notes`, as a
  defense-in-depth backstop even if a future call site logs one of these by mistake.
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
- SQLite database files (`*.db`), generated PDFs, and logs are git-ignored.

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
